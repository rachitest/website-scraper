# utils/storage/maxmind_geo.py

import os
import logging
import requests
import tarfile
import socket
import geoip2.database
import geoip2.errors
import dns.resolver
import dns.exception
import ssl
import OpenSSL.crypto
from OpenSSL import crypto
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, cast, Type, TypeVar, ClassVar
from utils.storage.s3_bucket import s3_manager
from types_def.utils.storage.maxmind_geo import GeoIPManager as GeoIPManagerProtocol

logger = logging.getLogger(__name__)

# Known CDN ASNs and their organizations
CDN_ASNS = {
    13335: "Cloudflare",
    16509: "Amazon CloudFront",
    20940: "Akamai",
    54113: "Fastly",
    15169: "Google Cloud CDN",
}

class GeoIPManager:
    """Manages MaxMind GeoIP database files and access."""
    
    _instance: ClassVar[Optional['GeoIPManager']] = None
    _initialized: bool = False
    city_db: str
    s3_key: str
    s3_prefix: str
    local_path: Path
    databases: Dict[str, str]
    
    def __new__(cls) -> 'GeoIPManager':
        if cls._instance is None:
            logger.info("Creating new GeoIPManager instance")
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        logger.info("Initializing GeoIP Manager...")
        
        # Initialize class attributes
        self.city_db = "GeoLite2-City.mmdb"
        self.s3_key = "geoip/GeoLite2-City.mmdb"
        self.s3_prefix = "geoip"
        self.databases = {}
        
        # Default to ~/Developer/volumes/GeoIP for local development
        self.local_path = Path.home() / "Developer" / "volumes" / "GeoIP"
        
        # Override with env var if set (e.g., for Docker)
        raw_path: Optional[str] = os.getenv("GEOIP_DB_PATH")
        if raw_path is not None:
            # Expand both ~ and $HOME - handle None case explicitly
            expanded_path = os.path.expandvars(raw_path)
            expanded_path = os.path.expanduser(expanded_path)
            logger.info(f"Using custom GEOIP_DB_PATH: {raw_path} (expanded to {expanded_path})")
            self.local_path = Path(expanded_path)
        else:
            logger.info(f"Using default path: {self.local_path}")
        
        # Ensure we can write to the directory
        self._ensure_directory_access()
        
        # Get database editions from environment
        editions = os.getenv("GEOIPUPDATE_EDITION_IDS", "GeoLite2-City GeoLite2-Country").split()
        logger.info(f"Configured database editions: {editions}")
        
        for edition in editions:
            db_type = edition.replace('GeoLite2-', '').lower()
            self.databases[db_type] = f"{edition}.mmdb"
        
        # Check databases on startup
        self._verify_databases()

    def _ensure_directory_access(self):
        """Ensure we have read/write access to the directory"""
        try:
            # Create all parent directories if they don't exist
            self.local_path.mkdir(parents=True, exist_ok=True)
            
            # Test write access by creating a temp file
            test_file = self.local_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            logger.info(f"Successfully verified access to {self.local_path}")
        except (PermissionError, OSError) as e:
            logger.error(f"Cannot access {self.local_path}: {e}")
            # Fall back to user's home directory if we can't access the preferred path
            self.local_path = Path.home() / ".geoip"
            self.local_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Falling back to {self.local_path}")
    
    def get_database_path(self):
        """Get path to GeoIP database, downloading if necessary"""
        db_path = self.local_path / self.city_db
        
        logger.info(f"Checking for GeoIP database at {db_path}")
        
        # Check if file exists and is a valid database
        if db_path.exists():
            try:
                # Try to open the database to verify it's valid
                with geoip2.database.Reader(str(db_path)) as reader:
                    # Test read to verify database is functional
                    reader.metadata()
                logger.info("✓ Found valid existing GeoIP database locally")
                return str(db_path)
            except Exception as e:
                logger.warning(f"✗ Existing database is invalid or corrupted: {e}")
                # Delete the invalid database
                try:
                    db_path.unlink()
                    logger.info("Removed invalid database file")
                except Exception as del_e:
                    logger.error(f"Failed to remove invalid database: {del_e}")
        else:
            logger.info("✗ No local database found, will attempt download")
        
        # Try S3 first
        logger.info("Attempting to download from S3...")
        if self.download_from_s3():
            # Verify the downloaded database
            try:
                with geoip2.database.Reader(str(db_path)) as reader:
                    reader.metadata()
                logger.info("✓ Successfully downloaded and verified database from S3")
                return str(db_path)
            except Exception as e:
                logger.error(f"✗ Downloaded database from S3 is invalid: {e}")
                db_path.unlink()
        else:
            logger.info("✗ S3 download failed or not configured, trying MaxMind...")
        
        # Fallback to MaxMind
        if self.download_from_maxmind():
            # Verify the downloaded database
            try:
                with geoip2.database.Reader(str(db_path)) as reader:
                    reader.metadata()
                logger.info("✓ Successfully downloaded and verified database from MaxMind")
                # Upload to S3 for future use
                logger.info("Attempting to cache database to S3 for future use...")
                self.upload_to_s3()
                return str(db_path)
            except Exception as e:
                logger.error(f"✗ Downloaded database from MaxMind is invalid: {e}")
                db_path.unlink()
        else:
            logger.error("✗ All download attempts failed")
        
        return None
    
    def download_from_s3(self):
        """Download database from S3"""
        return s3_manager.download_file(
            self.s3_key,
            self.local_path / self.city_db
        )
    
    def download_from_maxmind(self):
        """Download database from MaxMind"""
        license_key = os.getenv("MAXMIND_LICENSE_KEY")
        if not license_key:
            logger.info("✗ MAXMIND_LICENSE_KEY not set - skipping MaxMind download")
            return False
            
        try:
            logger.info("Downloading from MaxMind servers...")
            url = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save and extract
            logger.info("Download complete, extracting database...")
            tar_path = self.local_path / "GeoLite2-City.tar.gz"
            with open(tar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            with tarfile.open(tar_path) as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.mmdb'):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, self.local_path)
                        
            tar_path.unlink()  # Clean up tar file
            logger.info("✓ Successfully extracted GeoIP database")
            return True
        except Exception as e:
            logger.error(f"✗ MaxMind download failed: {e}")
            return False
    
    def upload_to_s3(self):
        """Upload database to S3 for future use"""
        return s3_manager.upload_file(
            self.local_path / self.city_db,
            self.s3_key
        )

    def _verify_databases(self):
        """Check for database files and download if missing"""
        logger.info("Verifying GeoIP databases...")
        missing_dbs = []
        
        for db_type, filename in self.databases.items():
            db_path = self.local_path / filename
            if db_path.exists():
                logger.info(f"✓ Found {db_type} database at {db_path}")
            else:
                logger.info(f"✗ Missing {db_type} database")
                missing_dbs.append(db_type)
        
        if missing_dbs:
            logger.info(f"Will attempt to download missing databases: {missing_dbs}")
            self._download_missing_databases(missing_dbs)
    
    def _download_missing_databases(self, db_types):
        """Download missing database files"""
        for db_type in db_types:
            filename = self.databases[db_type]
            s3_key = f"{self.s3_prefix}/{filename}"
            
            # Try S3 first
            logger.info(f"Attempting to download {db_type} database from S3...")
            if s3_manager.download_file(s3_key, self.local_path / filename):
                logger.info(f"✓ Successfully downloaded {db_type} database from S3")
                continue
            
            # Fallback to MaxMind
            logger.info(f"Attempting to download {db_type} database from MaxMind...")
            if self._download_from_maxmind(db_type):
                logger.info(f"✓ Successfully downloaded {db_type} database from MaxMind")
                # Cache to S3 for future use
                s3_manager.upload_file(self.local_path / filename, s3_key)
            else:
                logger.error(f"✗ Failed to download {db_type} database")

    def _download_from_maxmind(self, db_type):
        """Download specific database from MaxMind"""
        account_id = os.getenv("MAXMIND_ACCOUNT_ID")
        license_key = os.getenv("MAXMIND_LICENSE_KEY")
        # Preserve original case from environment variable
        edition_id = next(
            edition for edition in os.getenv("GEOIPUPDATE_EDITION_IDS", "").split()
            if edition.lower().endswith(db_type.lower())
        )
        
        if not (account_id and license_key):
            logger.info("✗ MaxMind credentials not configured")
            return False
        
        try:
            logger.info(f"Downloading {edition_id} from MaxMind...")
            url = f"https://download.maxmind.com/app/geoip_download?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz"
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save and extract
            logger.info("Download complete, extracting database...")
            tar_path = self.local_path / f"{edition_id}.tar.gz"
            with open(tar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            with tarfile.open(tar_path) as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.mmdb'):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, self.local_path)
                        
            tar_path.unlink()  # Clean up tar file
            logger.info(f"✓ Successfully extracted {edition_id} database")
            return True
        except Exception as e:
            logger.error(f"✗ MaxMind download failed for {edition_id}: {e}")
            return False

    def _get_dns_location_signals(self, domain: str) -> Dict[str, Any]:
        """Get location signals from DNS records"""
        signals = {
            'mx_records': [],
            'txt_records': [],
            'txt_ips': [],  # Extracted IPs from TXT records
            'txt_ip_locations': {},  # Location data for IPs found in TXT records
            'a_records': [],  # IPv4 addresses
            'aaaa_records': [],  # IPv6 addresses
            'soa_record': None,
            'soa_primary': None,  # Primary nameserver
            'soa_contact': None   # Contact email/domain
        }
        
        try:
            # A Records (IPv4)
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                signals['a_records'] = [str(rdata) for rdata in a_records]
                logger.info(f"Found A records: {signals['a_records']}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve A records: {e}")

            # AAAA Records (IPv6)
            try:
                aaaa_records = dns.resolver.resolve(domain, 'AAAA')
                signals['aaaa_records'] = [str(rdata) for rdata in aaaa_records]
                logger.info(f"Found AAAA records: {signals['aaaa_records']}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve AAAA records: {e}")

            # MX Records
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                signals['mx_records'] = [str(rdata) for rdata in mx_records]
                logger.info(f"Found MX records: {signals['mx_records']}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve MX records: {e}")

            # TXT Records and IP extraction
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')
                signals['txt_records'] = [str(rdata) for rdata in txt_records]
                # Extract IPs from SPF and other records
                for record in signals['txt_records']:
                    if 'ip4:' in record:
                        ips = [ip.strip() for ip in record.split('ip4:')[1:]]
                        extracted_ips = [ip.split()[0] for ip in ips]
                        signals['txt_ips'].extend(extracted_ips)
                        
                        # Look up location data for extracted IPs
                        for ip in extracted_ips:
                            try:
                                with geoip2.database.Reader(str(self.local_path / self.databases.get('city', 'GeoLite2-City.mmdb'))) as reader:
                                    response = reader.city(ip)
                                    signals['txt_ip_locations'][ip] = {
                                        'city': response.city.name,
                                        'country': response.country.name,
                                        'latitude': response.location.latitude,
                                        'longitude': response.location.longitude
                                    }
                            except Exception as e:
                                logger.warning(f"Could not get location for IP {ip}: {e}")
                                
                logger.info(f"Found TXT records: {signals['txt_records']}")
                if signals['txt_ips']:
                    logger.info(f"Extracted IPs from TXT: {signals['txt_ips']}")
                if signals['txt_ip_locations']:
                    logger.info(f"Found locations for TXT IPs: {signals['txt_ip_locations']}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve TXT records: {e}")

            # SOA Record with parsing
            try:
                soa_records = dns.resolver.resolve(domain, 'SOA')
                if soa_records:
                    soa = str(soa_records[0])
                    signals['soa_record'] = soa
                    # Parse SOA components
                    parts = soa.split()
                    if len(parts) >= 2:
                        signals['soa_primary'] = parts[0]  # Primary nameserver
                        signals['soa_contact'] = parts[1]  # Contact info
                    logger.info(f"Found SOA record: {soa}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve SOA record: {e}")

        except Exception as e:
            logger.error(f"Error getting DNS signals: {e}")

        return signals

    def _get_ssl_location_signals(self, domain: str) -> Dict[str, Optional[str]]:
        """Get location signals from SSL certificate"""
        signals: Dict[str, Optional[str]] = {
            'organization': None,
            'country': None,
            'state': None,
            'locality': None,
            'error': None,
            'issuer': None,
            'common_name': None,  # Adding CN field
            'issuer_country': None,  # Adding issuer country
            'issuer_common_name': None  # Adding issuer CN
        }
        
        try:
            # First attempt: Use requests with a session to ensure we can access the socket
            session = requests.Session()
            response = session.get(f'https://{domain}', verify=True)
            
            # Get the underlying socket from the connection
            if hasattr(response.raw, '_connection') and \
               hasattr(response.raw._connection, 'sock') and \
               response.raw._connection.sock is not None:
                cert = response.raw._connection.sock.getpeercert()
                logger.info(f"Raw certificate data: {cert}")
                
                if cert:
                    # Get subject information
                    if 'subject' in cert:
                        for key, value in cert['subject']:
                            if not isinstance(value, str):
                                continue
                            if key == 'organizationName':
                                signals['organization'] = value
                            elif key == 'countryName':
                                signals['country'] = value
                            elif key == 'stateOrProvinceName':
                                signals['state'] = value
                            elif key == 'localityName':
                                signals['locality'] = value
                            elif key == 'commonName':
                                signals['common_name'] = value
                    
                    # Get issuer information
                    if 'issuer' in cert:
                        for key, value in cert['issuer']:
                            if not isinstance(value, str):
                                continue
                            if key == 'organizationName':
                                signals['issuer'] = value
                            elif key == 'countryName':
                                signals['issuer_country'] = value
                            elif key == 'commonName':
                                signals['issuer_common_name'] = value
                        
                    logger.info(f"Found certificate info via requests: {signals}")
                    return signals

        except requests.exceptions.SSLError as e:
            error_msg = f"SSL verification failed: {str(e)}"
            logger.warning(error_msg)
            signals['error'] = error_msg
        except Exception as e:
            error_msg = f"Error getting certificate info via requests: {str(e)}"
            logger.error(error_msg)
            signals['error'] = error_msg
            
        # Fallback to direct SSL connection without verification
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert_bin = ssock.getpeercert(binary_form=True)
                    if not cert_bin:
                        raise ValueError("No certificate data received")
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_bin)
                    
                    # Get subject components
                    subject_components = dict(x509.get_subject().get_components())
                    logger.info(f"Certificate subject components: {subject_components}")
                    
                    # Get issuer components
                    issuer_components = dict(x509.get_issuer().get_components())
                    logger.info(f"Certificate issuer components: {issuer_components}")
                    
                    # Map the components to our signals
                    # Note: Components are in bytes, so we need to decode them
                    signals.update({
                        'organization': subject_components.get(b'O', b'').decode('utf-8') or None,
                        'country': subject_components.get(b'C', b'').decode('utf-8') or None,
                        'state': subject_components.get(b'ST', b'').decode('utf-8') or None,
                        'locality': subject_components.get(b'L', b'').decode('utf-8') or None,
                        'common_name': subject_components.get(b'CN', b'').decode('utf-8') or None,
                        'issuer': issuer_components.get(b'O', b'').decode('utf-8') or None,
                        'issuer_country': issuer_components.get(b'C', b'').decode('utf-8') or None,
                        'issuer_common_name': issuer_components.get(b'CN', b'').decode('utf-8') or None
                    })
                    
                    logger.info(f"Found certificate info via direct SSL: {signals}")
            
        except Exception as e:
            error_msg = f"SSL certificate lookup failed: {str(e)}"
            logger.error(error_msg)
            if not signals['error']:  # Don't overwrite previous error
                signals['error'] = error_msg
            
        return signals

    def _get_ip_location_signals(self, ip_address: str) -> Dict[str, Optional[str]]:
        """Get additional location signals from IP address"""
        signals = {
            'ip_ranges': [],
            'reverse_dns': None,
            'whois_info': None
        }
        
        try:
            # Try to get IP ranges from TXT records
            try:
                ptr_name = '.'.join(reversed(ip_address.split('.'))) + '.in-addr.arpa'
                txt_records = dns.resolver.resolve(ptr_name, 'TXT')
                signals['ip_ranges'] = [str(rdata) for rdata in txt_records]
                logger.info(f"Found IP TXT records: {signals['ip_ranges']}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException) as e:
                logger.warning(f"Could not retrieve IP TXT records: {e}")

            # Try reverse DNS lookup
            try:
                reverse_name = socket.gethostbyaddr(ip_address)[0]
                signals['reverse_dns'] = reverse_name
                logger.info(f"Found reverse DNS: {reverse_name}")
            except (socket.herror, socket.gaierror) as e:
                logger.warning(f"Could not perform reverse DNS lookup: {e}")

        except Exception as e:
            logger.error(f"Error getting IP signals: {e}")

        return signals

    def lookup_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get geolocation data for a URL by resolving its IP and querying MaxMind.
        Also checks additional signals if a CDN is detected.
        
        Args:
            url: The URL to lookup
            
        Returns:
            Dict containing location info and additional signals if behind CDN
        """
        try:
            # Parse domain from URL
            domain = urlparse(url).netloc
            if not domain:
                logger.error(f"Could not parse domain from URL: {url}")
                return None
                
            # Initialize result
            result = {
                'ip': None,
                'hostname': None,
                'city': None,
                'region': None,
                'country': None,
                'latitude': None,
                'longitude': None,
                'network': None,
                'is_cdn': False,
                'cdn_provider': None,
                'additional_signals': {}
            }

            # Resolve IP and do MaxMind lookups
            try:
                ip_address = socket.gethostbyname(domain)
                result['ip'] = ip_address
                logger.info(f"Resolved IP address: {ip_address}")
                
                # Get reverse hostname
                try:
                    hostname, _, _ = socket.gethostbyaddr(ip_address)
                    result['hostname'] = hostname
                    logger.info(f"Reverse hostname lookup: {hostname}")
                except socket.herror as e:
                    logger.warning(f"Reverse hostname lookup failed: {e}")

                # Do all database lookups
                self._do_maxmind_lookups(ip_address, result)
                
                # Check if this is a CDN
                if result.get('asn') in CDN_ASNS:
                    result['is_cdn'] = True
                    result['cdn_provider'] = CDN_ASNS[result['asn']]
                    logger.info(f"Detected CDN: {result['cdn_provider']}")
                    
                    # Get additional signals
                    logger.info("Getting additional location signals due to CDN detection")
                    result['additional_signals'] = {
                        'dns': self._get_dns_location_signals(domain),
                        'ssl': self._get_ssl_location_signals(domain),
                        'ip': self._get_ip_location_signals(ip_address),
                        'headers': self._get_header_signals(domain)
                    }
                
            except socket.gaierror as e:
                logger.error(f"Failed to resolve domain: {e}")
            
            logger.info(f"Final lookup results: {result}")
            return result
                
        except Exception as e:
            logger.error(f"Error during lookup: {e}")
            return None

    def _do_maxmind_lookups(self, ip_address: str, result: Dict[str, Any]) -> None:
        """Perform all MaxMind database lookups"""
        # Try city database first
        city_path = self.local_path / self.databases.get('city', 'GeoLite2-City.mmdb')
        if city_path.exists():
            try:
                with geoip2.database.Reader(str(city_path)) as reader:
                    city_response = reader.city(ip_address)
                    result.update({
                        'city': city_response.city.name,
                        'region': city_response.subdivisions.most_specific.name if city_response.subdivisions else None,
                        'country': city_response.country.name,
                        'latitude': city_response.location.latitude,
                        'longitude': city_response.location.longitude,
                        'network': str(city_response.traits.network) if hasattr(city_response.traits, 'network') else None
                    })
                    logger.info(f"City database lookup successful: {result}")
            except geoip2.errors.AddressNotFoundError:
                logger.warning(f"IP not found in city database: {ip_address}")
            except Exception as e:
                logger.error(f"Error querying city database: {e}")

        # If we don't have country data yet, try country database
        if not result['country']:
            country_path = self.local_path / self.databases.get('country', 'GeoLite2-Country.mmdb')
            if country_path.exists():
                try:
                    with geoip2.database.Reader(str(country_path)) as reader:
                        country_response = reader.country(ip_address)
                        result.update({
                            'country': country_response.country.name,
                            'continent': country_response.continent.name if hasattr(country_response, 'continent') else None
                        })
                        logger.info(f"Country database lookup successful: {result}")
                except geoip2.errors.AddressNotFoundError:
                    logger.warning(f"IP not found in country database: {ip_address}")
                except Exception as e:
                    logger.error(f"Error querying country database: {e}")

        # Try ASN database for network info
        asn_path = self.local_path / self.databases.get('asn', 'GeoLite2-ASN.mmdb')
        if asn_path.exists():
            try:
                with geoip2.database.Reader(str(asn_path)) as reader:
                    asn_response = reader.asn(ip_address)
                    result.update({
                        'asn': asn_response.autonomous_system_number,
                        'asn_org': asn_response.autonomous_system_organization,
                    })
                    logger.info(f"ASN database lookup successful: {result}")
            except geoip2.errors.AddressNotFoundError:
                logger.warning(f"IP not found in ASN database: {ip_address}")
            except Exception as e:
                logger.error(f"Error querying ASN database: {e}")

    def _get_header_signals(self, domain: str) -> Dict[str, Optional[str]]:
        """Get location signals from HTTP headers"""
        signals: Dict[str, Optional[str]] = {
            'server': None,
            'powered_by': None,
            'cf_ray': None,  # Full Cloudflare ray ID
            'cf_ray_location': None,  # Extracted location code from ray ID
            'cf_ipcountry': None,  # Cloudflare's detected country
            'server_timing': None,  # Raw server timing
            'server_rtt': None,  # Round trip time in ms
            'server_min_rtt': None,  # Minimum RTT observed
            'server_location': None,  # Extracted from timing info if available
            'estimated_distance_km': None  # Rough distance based on RTT
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; WebEntityScraper/1.0)',
                'Accept': '*/*'
            }
            
            response = requests.get(f'https://{domain}', headers=headers, allow_redirects=True)
            
            # Extract relevant headers
            if 'Server' in response.headers:
                signals['server'] = response.headers['Server']
            if 'X-Powered-By' in response.headers:
                signals['powered_by'] = response.headers['X-Powered-By']
            
            # Parse Cloudflare headers
            if 'CF-RAY' in response.headers:
                cf_ray = response.headers['CF-RAY']
                signals['cf_ray'] = cf_ray
                # Extract location code (e.g., "7ac7-SJC" -> "SJC")
                if '-' in cf_ray:
                    signals['cf_ray_location'] = cf_ray.split('-')[1]
                    
            if 'CF-IPCountry' in response.headers:
                signals['cf_ipcountry'] = response.headers['CF-IPCountry']
            
            # Parse Server-Timing header
            if 'Server-Timing' in response.headers:
                timing = response.headers['Server-Timing']
                signals['server_timing'] = timing
                
                # Extract timing information
                if 'rtt=' in timing:
                    try:
                        # Extract RTT values
                        rtt = timing.split('rtt=')[1].split('&')[0]
                        signals['server_rtt'] = rtt
                        
                        if 'min_rtt=' in timing:
                            min_rtt = timing.split('min_rtt=')[1].split('&')[0]
                            signals['server_min_rtt'] = min_rtt
                            
                            # Estimate rough distance based on min_rtt
                            # Speed of light in fiber is roughly 2/3 c, or 200,000 km/s
                            # Round trip means dividing by 2
                            # min_rtt is in microseconds, so divide by 1,000,000 for seconds
                            try:
                                min_rtt_seconds = float(min_rtt) / 1_000_000
                                distance_km = (min_rtt_seconds * 200_000) / 2
                                signals['estimated_distance_km'] = f"{distance_km:.0f}"
                            except ValueError:
                                pass
                    except Exception:
                        pass
            
            logger.info(f"Found header signals: {signals}")
            
        except Exception as e:
            logger.error(f"Error getting header signals: {e}")
            
        return signals

# Global instance
geoip_manager = GeoIPManager() 