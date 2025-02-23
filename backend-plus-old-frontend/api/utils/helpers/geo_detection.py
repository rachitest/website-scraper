# utils/helpers/geo_detection.py

"""
Geolocation detection utilities.

Provides functions for detecting and analyzing location information from various sources.
"""

import logging
import socket
import json
import re
from typing import Dict, List, Optional, Union, Any, cast
import geoip2.database
from utils.storage.maxmind_geo import geoip_manager
from utils.helpers.url_parsing import normalize_url
from urllib.parse import urlparse
from types_def.data import GeoLocation, LocationSignals, AddressInfo, LanguageRegion

logger = logging.getLogger(__name__)

def get_ip_location(url: str) -> Optional[GeoLocation]:
    """Get location information from IP address with fallback mechanisms"""
    try:
        domain = urlparse(normalize_url(url)).netloc
        ip = socket.gethostbyname(domain)
        logger.debug(f"Resolved IP for {domain}: {ip}")

        location_data: Dict[str, Union[str, float, None]] = {}
        
        # Try MaxMind City database first
        if 'city' in geoip_manager.databases:
            city_path = geoip_manager.local_path / geoip_manager.databases['city']
            if city_path.exists():
                try:
                    with geoip2.database.Reader(str(city_path)) as reader:
                        city_response = reader.city(ip)
                        location_data.update({
                            'country': city_response.country.name,
                            'city': city_response.city.name,
                            'latitude': city_response.location.latitude,
                            'longitude': city_response.location.longitude,
                        })
                except Exception as e:
                    logger.error(f"Error reading city database: {e}")

        # Add ASN data if available
        if 'asn' in geoip_manager.databases:
            asn_path = geoip_manager.local_path / geoip_manager.databases['asn']
            if asn_path.exists():
                try:
                    with geoip2.database.Reader(str(asn_path)) as reader:
                        asn_response = reader.asn(ip)
                        location_data.update({
                            'autonomous_system_number': asn_response.autonomous_system_number,
                            'autonomous_system_org': asn_response.autonomous_system_organization,
                        })
                except Exception as e:
                    logger.error(f"Error reading ASN database: {e}")

        # Add country-specific data if available
        if 'country' in geoip_manager.databases and not location_data.get('country'):
            country_path = geoip_manager.local_path / geoip_manager.databases['country']
            if country_path.exists():
                try:
                    with geoip2.database.Reader(str(country_path)) as reader:
                        country_response = reader.country(ip)
                        location_data.update({
                            'country': country_response.country.name,
                            'continent': country_response.continent.name
                        })
                except Exception as e:
                    logger.error(f"Error reading country database: {e}")

        if location_data:
            # Calculate confidence based on available data
            confidence = 0.0
            if location_data.get('city'):
                confidence += 0.4  # City-level data is most precise
            if location_data.get('country'):
                confidence += 0.2  # Country data
            if location_data.get('autonomous_system_org'):
                confidence += 0.2  # ASN data helps verify
            if location_data.get('latitude') and location_data.get('longitude'):
                confidence += 0.2  # Coordinate data
            
            result: GeoLocation = {
                'country': cast(Optional[str], location_data.get('country')),
                'city': cast(Optional[str], location_data.get('city')),
                'confidence': confidence,
                'source': 'maxmind'
            }
            logger.info(f"Location confidence score: {confidence} based on available data")
            logger.info(f"Location found via MaxMind: {json.dumps(result)}")
            return result

        # Fallback: Basic IP geolocation from common patterns
        if ip.startswith(('17.', '208.')):  # Apple/AWS US IPs
            return {
                'country': 'United States',
                'city': None,
                'confidence': 0.4,
                'source': 'ip_pattern'
            }
        elif ip.startswith(('34.', '35.')):  # Google Cloud
            return {
                'country': 'United States',
                'city': None,
                'confidence': 0.3,
                'source': 'ip_pattern'
            }
            
        logger.warning("No location data available")
        return None

    except Exception as e:
        logger.error(f"IP geolocation error: {str(e)}")
        return None

def detect_language_region(text: str) -> Optional[Dict[str, float]]:
    """Detect region based on language patterns"""
    try:
        # Dictionary of region-specific spellings
        us_spellings = {'color', 'flavor', 'center', 'theater', 'analyze', 'customize', 'honor'}
        non_us_spellings = {'colour', 'flavour', 'centre', 'theatre', 'analyse', 'customise', 'honour'}

        text_lower = text.lower()
        us_count = sum(1 for word in us_spellings if word in text_lower)
        non_us_count = sum(1 for word in non_us_spellings if word in text_lower)

        total = us_count + non_us_count
        if total == 0:
            logger.info("No regional spelling patterns found")
            return None

        result = {
            'US': us_count / total if total > 0 else 0,
            'Non-US': non_us_count / total if total > 0 else 0,
        }
        logger.info(f"Language region signals detected: {json.dumps(result)}")
        return result
    except Exception as e:
        logger.error(f"Language region detection error: {str(e)}")
        return None

def extract_addresses(text: str) -> List[AddressInfo]:
    """Extract potential address information from text"""
    # Simple pattern for US addresses
    us_address_pattern = r'\b\d+\s+[A-Za-z\s,]+(?:Road|Street|Ave|Avenue|Blvd|Boulevard|Rd|St|Dr|Drive|Lane|Ln|Place|Pl|Circle|Cir|Court|Ct|Highway|Hwy|Way)[,\s]+(?:[A-Za-z\s]+,\s*)?(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)[,\s]+\d{5}(?:-\d{4})?\b'

    # Non-US address pattern
    non_us_address_pattern = r'\b\d+\s+[A-Za-z\s,]+(?:Road|Street|Avenue|Lane|Court|Way|Close|Drive|Park|Gardens|Grove|Terrace)[,\s]+(?:[A-Za-z\s]+,\s*)?[A-Z]{1,2}[0-9][0-9A-Z]?\s+[0-9][A-Z]{2}\b'

    addresses: List[AddressInfo] = []
    us_addresses = re.findall(us_address_pattern, text, re.IGNORECASE)
    non_us_addresses = re.findall(non_us_address_pattern, text, re.IGNORECASE)

    for addr in us_addresses:
        addresses.append({
            'address': addr,
            'confidence': 0.9,
            'type': 'US'
        })
    for addr in non_us_addresses:
        addresses.append({
            'address': addr,
            'confidence': 0.9,
            'type': 'Non-US'
        })

    if addresses:
        logger.info(f"Extracted addresses: {json.dumps(addresses)}")
    return addresses

def combine_location_signals(
    ip_location: Optional[GeoLocation],
    language_region: Optional[Dict[str, float]],
    extracted_addresses: List[AddressInfo],
    content_location: Optional[str],
    social_equivalency: Optional[Dict[str, Any]]
) -> LocationSignals:
    """Combine different location signals using a weighted probability model"""
    try:
        location_weights = {
            'ip_geolocation': 0.25,
            'language_patterns': 0.1,
            'extracted_addresses': 0.3,
            'content_mentions': 0.25,
            'social_equivalency': 0.1
        }

        location_scores: Dict[str, Any] = {}
        confidence: float = 0.0
        signals_used: List[str] = []
        final_location: Optional[str] = None

        # Process IP location
        if ip_location:
            # Safely get confidence value as float
            ip_confidence = float(ip_location['confidence'])
            confidence_score = ip_confidence * location_weights['ip_geolocation']

            location_scores['ip'] = {
                'country': ip_location['country'],
                'city': ip_location['city'],
                'confidence': confidence_score
            }
            confidence += confidence_score
            signals_used.append(f"IP Geolocation ({ip_location['source']})")

        # Process language patterns
        if language_region:
            max_region = max(language_region.items(), key=lambda x: x[1])
            confidence_score = float(max_region[1]) * location_weights['language_patterns']
            location_scores['language'] = {
                'region': max_region[0],
                'confidence': confidence_score
            }
            confidence += confidence_score
            signals_used.append(f"Language Analysis ({max_region[0]})")

        # Process extracted addresses
        if extracted_addresses:
            # Safely get max confidence as float
            max_confidence = max(float(addr['confidence']) for addr in extracted_addresses)
            confidence_score = max_confidence * location_weights['extracted_addresses']
            
            location_scores['addresses'] = {
                'locations': extracted_addresses,
                'confidence': confidence_score
            }
            confidence += confidence_score
            signals_used.append("Address Extraction")

        # Determine final location
        if location_scores:
            if 'addresses' in location_scores and extracted_addresses:
                final_location = extracted_addresses[0]['address']
            elif 'ip' in location_scores and location_scores['ip'].get('city'):
                final_location = f"{location_scores['ip']['city']}, {location_scores['ip']['country']}"
            elif 'language' in location_scores:
                final_location = f"Likely {location_scores['language']['region']} based on language patterns"

        result: LocationSignals = {
            'location': final_location,
            'confidence': round(confidence, 2),
            'signals': location_scores,
            'signals_used': signals_used,
            'error': None
        }

        logger.info(f"Final combined location result: {json.dumps(result)}")
        return result
    except Exception as e:
        logger.error(f"Error combining location signals: {str(e)}")
        return {
            'location': None,
            'confidence': 0,
            'signals': {},
            'signals_used': [],
            'error': str(e)
        } 