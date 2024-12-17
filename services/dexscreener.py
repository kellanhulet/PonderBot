import aiohttp
import re
from typing import Optional, Dict, Any

class DexScreenerService:
    BASE_URL = "https://api.dexscreener.com"

    @staticmethod
    def is_valid_pair_id(token_address: str) -> bool:
        # Validate if the pair ID is valid (44 chars, alphanumeric)
        if len(token_address) < 42:
            return False
        return bool(re.match("^[a-zA-Z0-9]*$", token_address))
    
    @staticmethod
    async def fetch_pair_info(token_address: str) -> Optional[Dict[str, Any]]:
        # Fetch pair information from DexScreener API
        url = f"{DexScreenerService.BASE_URL}/latest/dex/tokens/{token_address}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data.get("pairs") and len(data["pairs"]) > 0:
                        return data["pairs"][0]
                return None
    
    @staticmethod
    async def fetch_rugcheck(token_address: str) -> Optional[Dict[str, Any]]:
        # Fetch pair information from DexScreener API
        url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
        print(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(response.status)
                if response.status == 200:
                    data = await response.json()
                    print(data)
                    if data:
                        return data
                return None
    
    @staticmethod
    async def fetch_(token_address: str) -> Optional[Dict[str, Any]]:
        # Fetch pair information from DexScreener API
        url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report/summary"
        print(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(response.status)
                if response.status == 200:
                    data = await response.json()
                    print(data)
                    if data:
                        return data
                return None

    @staticmethod
    async def fetch_first_token_url() -> Optional[str]:
        # Fetches the first token profile URL from DexScreener API
        # Returns: URL string or None if not found/error
        async with aiohttp.ClientSession() as session:
            url = f"{DexScreenerService.BASE_URL}/token-profiles/latest/v1"
            async with session.get(DexScreenerService.BASE_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return data[0].get('url')
                return None