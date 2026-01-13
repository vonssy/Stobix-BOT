from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    BasicAuth
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from datetime import datetime, timezone
from colorama import *
import asyncio, random, json, pytz, re, os

wib = pytz.timezone('Asia/Jakarta')

class Stobix:
    def __init__(self) -> None:
        self.BASE_API = "https://api.stobix.com/v1"
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.auth_tokens = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Stobix App {Fore.BLUE + Style.BRIGHT}Auto BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def load_accounts(self):
        filename = "accounts.txt"
        try:
            with open(filename, 'r') as file:
                accounts = [line.strip() for line in file if line.strip()]
            return accounts
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Accounts: {e}{Style.RESET_ALL}")
            return None

    def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def build_proxy_config(self, proxy_url=None):
        if not proxy_url:
            return None, None, None

        if proxy_url.startswith("socks"):
            connector = ProxyConnector.from_url(proxy_url)
            return connector, None, None

        elif proxy_url.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy_url)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy_url, None

        raise Exception("Unsupported Proxy Type.")
        
    def generate_address(self, account: str):
        try:
            account = Account.from_key(account)
            address = account.address

            return address
        except Exception as e:
            return None
    
    def generate_payload(self, account: str, auth_nonce: dict):
        try:
            encoded_message = encode_defunct(text=auth_nonce["message"])
            signed_message = Account.sign_message(encoded_message, private_key=account)
            signature = to_hex(signed_message.signature)

            payload = {
                "nonce": auth_nonce["nonce"],
                "signature": signature
            }

            return payload
        except Exception as e:
            raise Exception(f"Generate Req Payload Failed: {str(e)}")
    
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None

    def print_question(self):
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2] -> {Style.RESET_ALL}").strip())

                if proxy_choice in [1, 2]:
                    proxy_type = (
                        "With" if proxy_choice == 1 else 
                        "Without"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1, or 2.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1, or 2).{Style.RESET_ALL}")

        rotate_proxy = False
        if proxy_choice == 1:
            while True:
                rotate_proxy = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()

                if rotate_proxy in ["y", "n"]:
                    rotate_proxy = rotate_proxy == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

        return proxy_choice, rotate_proxy
    
    async def check_connection(self, proxy_url=None):
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Connection Not 200 OK {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
        
        return None
    
    async def auth_nonce(self, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/auth/nonce"
        data = json.dumps({"address":address})
        headers = {
            **self.HEADERS[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Failed to Fetch Nonce {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def auth_verify(self, account: str, address: str, auth_nonce: dict, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/auth/web3/verify"
        data = json.dumps(self.generate_payload(account, auth_nonce))
        headers = {
            **self.HEADERS[address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Login Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def user_loyality(self, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/loyalty"
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.auth_tokens[address]}"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Status :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Failed to Fetch Loyality {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def perform_mining(self, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/loyalty/points/mine"
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.auth_tokens[address]}",
            "Content-Length": "0"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.BLUE + Style.BRIGHT}   Start :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def claim_mining(self, address: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/loyalty/points/claim"
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.auth_tokens[address]}",
            "Content-Length": "0"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.BLUE + Style.BRIGHT}   Claim :{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Failed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def claim_tasks(self, address: str, task_id: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/loyalty/tasks/claim"
        data = json.dumps({"taskId":task_id})
        headers = {
            **self.HEADERS[address],
            "Authorization": f"Bearer {self.auth_tokens[address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        result = await response.json()

                        if response.status == 400:
                            err_msg = result.get("error", "Unknown")
                            self.log(
                                f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                                f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                                f"{Fore.YELLOW + Style.BRIGHT} {err_msg} {Style.RESET_ALL}"
                            )
                            return None
                        
                        response.raise_for_status()
                        return result
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Not Claimed {Style.RESET_ALL}"
                    f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
                )
        
        return None
    
    async def process_check_connection(self, address: str, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy  :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {proxy} {Style.RESET_ALL}"
            )

            is_valid = await self.check_connection(proxy)
            if is_valid: return True

            if rotate_proxy:
                proxy = self.rotate_proxy_for_account(address)
                await asyncio.sleep(1)
                continue

            return False

    async def process_auth_verify(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        is_valid = await self.process_check_connection(address, use_proxy, rotate_proxy)
        if is_valid:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None

            auth_nonce = await self.auth_nonce(address, proxy)
            if not auth_nonce: return False

            auth_verify = await self.auth_verify(account, address, auth_nonce, proxy)
            if not auth_verify: return False

            self.auth_tokens[address] = auth_verify.get("token")

            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.GREEN + Style.BRIGHT} Login Success {Style.RESET_ALL}"
            )

            return True
        
    async def process_accounts(self, account: str, address: str, use_proxy: bool, rotate_proxy: bool):
        verifed = await self.process_auth_verify(account, address, use_proxy, rotate_proxy)
        if verifed:
            proxy = self.get_next_proxy_for_account(address) if use_proxy else None
            
            loyality = await self.user_loyality(address, proxy)
            if not loyality: return False
            
            points = loyality.get("user", {}).get("points", 0)
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Balance:{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {points} $SBXP {Style.RESET_ALL}"
            )

            self.log(f"{Fore.CYAN + Style.BRIGHT}Mining :{Style.RESET_ALL}")

            mining_ts = loyality.get("user", {}).get("miningStartedAt", None)

            if mining_ts is None:
                self.log(
                    f"{Fore.BLUE + Style.BRIGHT}   Status:{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} Ready to Start {Style.RESET_ALL}"
                )

                start = await self.perform_mining(address, proxy)
                if start:
                    self.log(
                        f"{Fore.BLUE + Style.BRIGHT}   Start :{Style.RESET_ALL}"
                        f"{Fore.GREEN + Style.BRIGHT} Success {Style.RESET_ALL}"
                    )

            else:
                mining_claim_ts = loyality.get("user", {}).get("miningClaimAt", None)
                claim_datetime = datetime.fromisoformat(mining_claim_ts.replace("Z", "+00:00"))

                datetime_now = datetime.now(timezone.utc)

                if datetime_now > claim_datetime:
                    mining_reward = loyality.get("user", {}).get("miningAmount", None)

                    self.log(
                        f"{Fore.BLUE + Style.BRIGHT}   Status:{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} Ready to Claim {Style.RESET_ALL}"
                    )

                    claim = await self.claim_mining(address, proxy)
                    if claim:
                        self.log(
                            f"{Fore.BLUE + Style.BRIGHT}   Claim :{Style.RESET_ALL}"
                            f"{Fore.GREEN + Style.BRIGHT} Success {Style.RESET_ALL}"
                        )
                        self.log(
                            f"{Fore.BLUE + Style.BRIGHT}   Reward:{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {mining_reward} $SBXP {Style.RESET_ALL}"
                        )

                        start = await self.perform_mining(address, proxy)
                        if start:
                            self.log(
                                f"{Fore.BLUE + Style.BRIGHT}   Start :{Style.RESET_ALL}"
                                f"{Fore.GREEN + Style.BRIGHT} Success {Style.RESET_ALL}"
                            )

                else:
                    formatted_claim_dt = claim_datetime.astimezone(wib).strftime('%x %X %Z')
                    self.log(
                        f"{Fore.BLUE + Style.BRIGHT}   Status:{Style.RESET_ALL}"
                        f"{Fore.YELLOW + Style.BRIGHT} Not Ready {Style.RESET_ALL}"
                    )
                    self.log(
                        f"{Fore.BLUE + Style.BRIGHT}   Ready :{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {formatted_claim_dt} {Style.RESET_ALL}"
                    )

            self.log(f"{Fore.CYAN + Style.BRIGHT}Tasks  :{Style.RESET_ALL}")

            tasks = loyality.get("tasks", [])
            for task in tasks:
                task_id = task.get("id")
                reward = task.get("points")
                frequency = task.get("frequency")
                claimed_at = task.get("claimedAt")

                if frequency == "once":

                    if claimed_at is not None:
                        self.log(
                            f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                            f"{Fore.YELLOW + Style.BRIGHT} Already Completed {Style.RESET_ALL}"
                        )
                        continue

                    if task_id in [
                        "make_deposit", "create_futures", "create_dual", "become_ambassador"
                    ]:
                        self.log(
                            f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                            f"{Fore.YELLOW + Style.BRIGHT} Skipped {Style.RESET_ALL}"
                        )
                        continue

                    claim = await self.claim_tasks(address, task_id, proxy)
                    if claim:
                        self.log(
                            f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                            f"{Fore.GREEN + Style.BRIGHT} Claimed {Style.RESET_ALL}"
                            f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT} Reward: {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{reward} $SBXP{Style.RESET_ALL}"
                        )

                elif frequency == "daily":
                    claim = await self.claim_tasks(address, task_id, proxy)
                    if claim:
                        self.log(
                            f"{Fore.GREEN + Style.BRIGHT} ● {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{task_id}{Style.RESET_ALL}"
                            f"{Fore.GREEN + Style.BRIGHT} Claimed {Style.RESET_ALL}"
                            f"{Fore.MAGENTA + Style.BRIGHT}-{Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT} Reward: {Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT}{reward} $SBXP{Style.RESET_ALL}"
                        )

    async def main(self):
        try:
            accounts = self.load_accounts()
            if not accounts: return

            proxy_choice, rotate_proxy = self.print_question()

            while True:
                self.clear_terminal()
                self.welcome()
                self.log(
                    f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}"
                )

                use_proxy = True if proxy_choice == 1 else False
                if use_proxy: self.load_proxies()

                separator = "=" * 25
                for account in accounts:
                    if account:
                        address = self.generate_address(account)
                        self.log(
                            f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                            f"{Fore.WHITE + Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                            f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                        )

                        if not address:
                            self.log(
                                f"{Fore.CYAN + Style.BRIGHT}Status :{Style.RESET_ALL}"
                                f"{Fore.RED + Style.BRIGHT} Invalid Private Key or Library Version Not Supported {Style.RESET_ALL}"
                            )
                            continue

                        self.HEADERS[address] = {
                            "Accept": "application/json, text/plain, */*",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Cache-Control": "no-cache",
                            "Origin": "https://app.stobix.com",
                            "Pragma": "no-cache",
                            "Referer": "https://app.stobix.com/",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-site",
                            "User-Agent": FakeUserAgent().random
                        }
                        
                        await self.process_accounts(account, address, use_proxy, rotate_proxy)
                        await asyncio.sleep(random.uniform(2.0, 3.0))

                self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}"*72)
                
                delay = 8 * 60 * 60
                while delay > 0:
                    formatted_time = self.format_seconds(delay)
                    print(
                        f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                        f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                        f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed...{Style.RESET_ALL}",
                        end="\r",
                        flush=True
                    )
                    await asyncio.sleep(1)
                    delay -= 1

        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Error: {e}{Style.RESET_ALL}")
            raise e

if __name__ == "__main__":
    try:
        bot = Stobix()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Stobix App - BOT{Style.RESET_ALL}                                       "                              
        )