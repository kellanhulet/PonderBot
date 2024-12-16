import aiohttp
from typing import Optional

class DexScreenerService:
    BASE_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    @staticmethod
    async def fetch_first_token_url() -> Optional[str]:
        """
        Fetches the first token profile URL from DexScreener API
        Returns: URL string or None if not found/error
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(DexScreenerService.BASE_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return data[0].get('url')
                return None