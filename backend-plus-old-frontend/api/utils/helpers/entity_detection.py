# utils/helpers/entity_detection.py

"""
Entity detection utilities.

Provides functions for detecting and analyzing entities from website content.
"""

import logging
import json
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from utils.helpers.url_parsing import normalize_url
import re
import difflib
from typing import Dict, List, Tuple, Optional, Any, Union, cast
from types_def.data import SocialEquivalency

logger = logging.getLogger(__name__)

def extract_social_links(soup: BeautifulSoup, base_url: str) -> Tuple[Dict[str, Union[str, Dict[str, Any]]], List[str]]:
    """Extract social media links more comprehensively"""
    base_url = normalize_url(base_url)
    social_patterns = {
        'twitter': ['twitter.com', 'x.com'],
        'linkedin': ['linkedin.com'],
        'github': ['github.com'],
        'instagram': ['instagram.com'],
        'facebook': ['facebook.com', 'fb.com'],
        'discord': ['discord.com', 'discord.gg'],
    }

    social_links: Dict[str, Union[str, Dict[str, Any]]] = {}
    all_links: List[str] = []  # Store all links for equivalency analysis

    for platform, domains in social_patterns.items():
        for link in soup.find_all('a', href=True):
            if not isinstance(link, Tag):
                continue
                
            href = link.get('href')
            if not href:
                continue

            # Make relative URLs absolute
            if not isinstance(href, str):
                continue
                
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)

            if any(domain in href.lower() for domain in domains):
                social_links[platform] = href
                all_links.append(href)
                break

    logger.info(f"Found social links: {json.dumps(social_links)}")
    return social_links, all_links

def analyze_social_equivalency(social_links: Dict[str, Union[str, Dict[str, Any]]]) -> Optional[SocialEquivalency]:
    """Match social media profiles that likely belong to the same entity"""
    try:
        if not social_links:
            return None
        
        # Extract usernames/handles from URLs
        identities: Dict[str, str] = {}
        for platform, url_data in social_links.items():
            url = url_data if isinstance(url_data, str) else url_data.get('url', '')
            match = re.search(r'(?:com|net)/([^/]+)/?$', url)
            if match:
                identities[platform] = match.group(1)
        
        if not identities:
            return None

        # Get the most common username pattern
        usernames = list(identities.values())
        if not usernames:
            return None

        # Use the first username as reference
        reference_username = usernames[0]
        reference_platform = list(identities.keys())[0]
        
        # Compare identities for similarity
        matches: List[str] = []
        total_similarity = 0.0
        
        for platform, username in identities.items():
            if platform != reference_platform:
                similarity = difflib.SequenceMatcher(None, reference_username, username).ratio()
                if similarity > 0.7:  # High similarity threshold
                    matches.append(platform)
                total_similarity += similarity

        average_similarity = total_similarity / len(identities) if identities else 0
        
        result: SocialEquivalency = {
            'platform': reference_platform,
            'username': reference_username,
            'confidence': average_similarity,
            'matches': matches
        }
        
        return result
    except Exception as e:
        logger.error(f"Social equivalency analysis error: {str(e)}")
        return None 