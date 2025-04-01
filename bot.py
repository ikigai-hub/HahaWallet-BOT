from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import *
import asyncio, json, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class HahaWallet:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "chrome-extension://andhndehpcjpmneneealacgnmealilal",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "none",
            "User-Agent": FakeUserAgent().random,
            "X-Request-Source-Extra": "chrome"
        }
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]"
            f"{Fore.WHITE} | {message}{Style.RESET_ALL}",
            flush=True
        )

    def welcome(self):
        print(f"""
{Fore.GREEN}Auto Claim Karma {Fore.BLUE}Haha Wallet - BOT
{Fore.GREEN}Rey? {Fore.YELLOW}<INI WATERMARK>
        """)

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def load_accounts(self):
        try:
            if not os.path.exists('accounts.json'):
                self.log(f"{Fore.RED}File 'accounts.json' not found")
                return []

            with open('accounts.json') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"{Fore.RED}Error loading accounts: {e}")
            return []
        
    async def load_proxies(self, choice: int):
        try:
            if choice == 1:
                async with ClientSession() as session:
                    async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt") as res:
                        self.proxies = (await res.text()).splitlines()
                        with open("proxy.txt", "w") as f:
                            f.write("\n".join(self.proxies))
            else:
                with open("proxy.txt") as f:
                    self.proxies = f.read().splitlines()
            
            self.log(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies")
        
        except Exception as e:
            self.log(f"{Fore.RED}Proxy error: {e}")
            self.proxies = []

    def get_proxy(self, account):
        if not self.proxies:
            return None
            
        if account not in self.account_proxies:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            self.account_proxies[account] = self.format_proxy(proxy)
            self.proxy_index += 1
            
        return self.account_proxies[account]

    def format_proxy(self, proxy):
        if not proxy.startswith(("http://", "https://")):
            return f"http://{proxy}"
        return proxy
    
    def mask_email(self, email):
        user, domain = email.split('@', 1)
        return f"{user[:3]}***{user[-3:]}@{domain}"

    async def user_login(self, email: str, pwd: str, proxy=None):
        url = "https://prod.haha.me/users/login"
        for _ in range(3):
            try:
                async with ClientSession() as session:
                    async with session.post(
                        url,
                        headers=self.headers,
                        json={"email": email, "password": pwd},
                        proxy=proxy,
                        timeout=ClientTimeout(60)
                    ) as res:
                        res.raise_for_status()
                        return (await res.json())['id_token']
            except Exception as e:
                self.log(f"{Fore.RED}Login failed: {type(e).__name__}")
                await asyncio.sleep(5)
        return None

    async def get_balance(self, token: str, proxy=None):
        try:
            async with ClientSession() as session:
                async with session.post(
                    "https://prod.haha.me/wallet-api/graphql",
                    headers={**self.headers, "Authorization": token},
                    json={"query": "{ getKarmaPoints }"},
                    proxy=proxy,
                    timeout=ClientTimeout(60)
                ) as res:
                    res.raise_for_status()
                    return (await res.json())['data']['getKarmaPoints']
        except Exception:
            return "N/A"

    async def handle_checkin(self, token: str, proxy=None):
        try:
            async with ClientSession() as session:
                # Check checkin status
                async with session.post(
                    "https://prod.haha.me/wallet-api/graphql",
                    headers={**self.headers, "Authorization": token},
                    json={"query": "query { getDailyCheckIn(timezone: \"Asia/Jakarta\") }"},
                    proxy=proxy,
                    timeout=ClientTimeout(60)
                ) as res:
                    status = (await res.json())['data']['getDailyCheckIn']

                if status:
                    # Claim checkin
                    async with session.post(
                        "https://prod.haha.me/wallet-api/graphql",
                        headers={**self.headers, "Authorization": token},
                        json={"query": "mutation { setDailyCheckIn(timezone: \"Asia/Jakarta\") }"},
                        proxy=proxy,
                        timeout=ClientTimeout(60)
                    ) as res:
                        await res.json()
                    return True
                return False
        except Exception:
            return None

    async def process_account(self, email: str, pwd: str, use_proxy: bool):
        proxy = self.get_proxy(email) if use_proxy else None
        masked_email = self.mask_email(email)
        
        # Login
        token = await self.user_login(email, pwd, proxy)
        if not token:
            self.log(f"{Fore.RED}{masked_email} - Login failed")
            return

        self.log(f"{Fore.GREEN}{masked_email} - Login success")
        self.log(f"{Fore.CYAN}Using proxy: {proxy or 'None'}")

        # Get balance
        balance = await self.get_balance(token, proxy)
        self.log(f"{Fore.CYAN}Balance: {Fore.WHITE}{balance} Karma")

        # Handle checkin
        checkin_result = await self.handle_checkin(token, proxy)
        if checkin_result is None:
            self.log(f"{Fore.RED}Checkin status check failed")
        elif checkin_result:
            new_balance = await self.get_balance(token, proxy)
            self.log(f"{Fore.GREEN}Checkin claimed! New balance: {new_balance}")
        else:
            self.log(f"{Fore.YELLOW}Already checked in today")

        # Add task claiming logic here...

    async def main(self):
        accounts = self.load_accounts()
        if not accounts:
            return

        print("1. Use Monosans proxies\n2. Use local proxies\n3. No proxies")
        choice = int(input("Select: ").strip())
        use_proxy = choice in (1, 2)
        
        if use_proxy:
            await self.load_proxies(choice)

        while True:
            self.clear_terminal()
            self.welcome()
            
            tasks = []
            for acc in accounts:
                tasks.append(
                    self.process_account(
                        acc['Email'],
                        acc['Password'],
                        use_proxy
                    )
                )
            
            await asyncio.gather(*tasks)
            
            self.log(f"{Fore.CYAN}Cycle completed. Restarting in 12 hours...")
            await asyncio.sleep(12 * 3600)

if __name__ == "__main__":
    try:
        asyncio.run(HahaWallet().main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Exited")
