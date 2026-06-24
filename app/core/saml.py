from __future__ import annotations

import base64
import uuid as _uuid
import zlib
from xml.etree import ElementTree as ET

import structlog
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

logger = structlog.get_logger()

SAML2_NAMESPACE = "urn:oasis:names:tc:SAML:2.0:"
NSMAP = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


class SamlSPClient:
    def __init__(
        self,
        *,
        entity_id: str,
        acs_url: str,
        idp_metadata_url: str,
        idp_sso_url: str = "",
        idp_entity_id: str = "",
        idp_cert: str = "",
        sp_key: str = "",
        sp_cert: str = "",
    ):
        self.entity_id = entity_id
        self.acs_url = acs_url
        self.idp_metadata_url = idp_metadata_url
        self.idp_sso_url = idp_sso_url
        self.idp_entity_id = idp_entity_id
        self.idp_cert_pem = idp_cert
        self.sp_key_pem = sp_key
        self.sp_cert_pem = sp_cert

    def create_sp_metadata(self) -> str:
        """Generate SAML SP metadata XML for IdP registration."""
        md = ET.Element(f"{{{NSMAP['md']}}}EntityDescriptor", {"entityID": self.entity_id})
        sp_sso = ET.SubElement(
            md,
            f"{{{NSMAP['md']}}}SPSSODescriptor",
            {
                "protocolSupportEnumeration": "urn:oasis:names:tc:SAML:2.0:protocol",
                "AuthnRequestsSigned": "true" if self.sp_key_pem else "false",
            },
        )
        ET.SubElement(
            sp_sso,
            f"{{{NSMAP['md']}}}AssertionConsumerService",
            {
                "Binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                "Location": self.acs_url,
                "index": "0",
                "isDefault": "true",
            },
        )
        return ET.tostring(md, encoding="unicode", xml_declaration=True)

    def create_login_url(self) -> str:
        """Build a SAML AuthnRequest URL (HTTP-Redirect binding)."""
        request_id = f"_{_uuid.uuid4().hex}"
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        issue_instant = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        root = ET.Element(
            f"{{{NSMAP['samlp']}}}AuthnRequest",
            {
                "ID": request_id,
                "Version": "2.0",
                "IssueInstant": issue_instant,
                "Destination": self.idp_sso_url,
                "ProtocolBinding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                "AssertionConsumerServiceURL": self.acs_url,
            },
        )
        ET.SubElement(root, f"{{{NSMAP['saml']}}}Issuer").text = self.entity_id
        ET.SubElement(
            root,
            f"{{{NSMAP['samlp']}}}NameIDPolicy",
            {
                "Format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "AllowCreate": "true",
            },
        )

        xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=False)
        compressed = zlib.compress(xml_str)[2:-4]
        encoded = base64.b64encode(compressed).decode("utf-8")

        query_params = f"SAMLRequest={__import__('urllib.parse').quote(encoded)}"
        if self.idp_sso_url and "?" in self.idp_sso_url:
            return f"{self.idp_sso_url}&{query_params}"
        separator = "&" if "?" in (self.idp_sso_url or "") else "?"
        return f"{self.idp_sso_url}{separator}{query_params}"

    def parse_authn_response(self, saml_response: str) -> dict:
        """Decode and parse a SAML AuthnResponse, verify signature, return claims."""
        raw = base64.b64decode(saml_response)
        root = ET.fromstring(raw)

        status_code_el = root.find(f".//{{{NSMAP['samlp']}}}StatusCode")
        if status_code_el is not None:
            status_val = status_code_el.get("Value", "")
            if "Success" not in status_val:
                raise ValueError(f"SAML response status: {status_val}")

        assertion = root.find(f".//{{{NSMAP['saml']}}}Assertion")
        if assertion is None:
            raise ValueError("No Assertion element in SAML response")

        self._verify_signature(assertion)

        name_id_el = assertion.find(f".//{{{NSMAP['saml']}}}Subject/{{{NSMAP['saml']}}}NameID")
        name_id = name_id_el.text if name_id_el is not None else ""

        attributes: dict[str, list[str]] = {}
        attr_stmt = assertion.find(f"{{{NSMAP['saml']}}}AttributeStatement")
        if attr_stmt is not None:
            for attr in attr_stmt.findall(f"{{{NSMAP['saml']}}}Attribute"):
                attr_name = attr.get("Name", "")
                values = [v.text or "" for v in attr.findall(f"{{{NSMAP['saml']}}}AttributeValue")]
                attributes[attr_name] = values

        return {"name_id": name_id, "attributes": attributes}

    def _verify_signature(self, assertion: ET.Element) -> None:
        signature = assertion.find(f".//{{{NSMAP['ds']}}}Signature")
        if signature is None:
            return

        signed_info = signature.find(f"{{{NSMAP['ds']}}}SignedInfo")
        sig_value_el = signature.find(f"{{{NSMAP['ds']}}}SignatureValue")
        if signed_info is None or sig_value_el is None:
            return

        canon_method = signed_info.find(f"{{{NSMAP['ds']}}}CanonicalizationMethod")
        canon_algorithm = canon_method.get("Algorithm", "") if canon_method is not None else ""

        sig_method = signed_info.find(f"{{{NSMAP['ds']}}}SignatureMethod")
        sig_algorithm = sig_method.get("Algorithm", "") if sig_method is not None else ""

        sig_value = sig_value_el.text or ""

        if not self.idp_cert_pem:
            return

        cert = x509.load_pem_x509_certificate(self.idp_cert_pem.encode())
        public_key = cert.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            return

        hash_alg: hashes.HashAlgorithm
        match sig_algorithm:
            case "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256":
                hash_alg = hashes.SHA256()
            case "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512":
                hash_alg = hashes.SHA512()
            case _:
                hash_alg = hashes.SHA256()

        sig_bytes = base64.b64decode(sig_value)
        signed_info_bytes = self._canonicalize(signed_info, canon_algorithm)

        try:
            public_key.verify(  # type: ignore[call-overload]
                sig_bytes, signed_info_bytes, padding=None, algorithm=hash_alg
            )
        except InvalidSignature:
            raise ValueError("SAML assertion signature verification failed") from None

    @staticmethod
    def _canonicalize(element: ET.Element, _algorithm: str) -> bytes:
        xml_bytes = ET.tostring(element, encoding="utf-8", xml_declaration=False)
        return ET.canonicalize(xml_bytes.decode("utf-8"), strip_text=True).encode("utf-8")


def build_saml_client(*, acs_url: str = "") -> SamlSPClient | None:
    """Create a SAML SP client from settings. Returns None if not configured."""
    if not settings.auth_saml_enabled:
        return None

    metadata_url = settings.auth_saml_idp_metadata_url
    if not metadata_url:
        logger.info("saml_missing_idp_metadata_url")
        return None

    sp_key = (
        settings.auth_saml_sp_private_key.get_secret_value()
        if settings.auth_saml_sp_private_key
        else ""
    )
    sp_cert = settings.auth_saml_sp_cert.get_secret_value() if settings.auth_saml_sp_cert else ""

    client = SamlSPClient(
        entity_id=settings.auth_saml_sp_entity_id,
        acs_url=acs_url,
        idp_metadata_url=metadata_url,
        idp_sso_url="",
        idp_entity_id="",
        idp_cert="",
        sp_key=sp_key,
        sp_cert=sp_cert,
    )
    if metadata_url:
        try:
            metadata_xml = __import__("httpx").get(metadata_url, timeout=10).text
            _load_idp_metadata(client, metadata_xml)
        except Exception as e:
            logger.warning("saml_load_metadata_failed", error=str(e))
    return client


def _load_idp_metadata(client: SamlSPClient, xml_str: str) -> None:
    root = ET.fromstring(xml_str)
    entity_id_attr = root.get("entityID", "")
    if entity_id_attr:
        client.idp_entity_id = entity_id_attr

    sso_desc = root.find(f".//{{{NSMAP['md']}}}IDPSSODescriptor")
    if sso_desc is not None:
        for sso_svc in sso_desc.findall(f"{{{NSMAP['md']}}}SingleSignOnService"):
            binding = sso_svc.get("Binding", "")
            if "HTTP-Redirect" in binding:
                location = sso_svc.get("Location", "")
                if location:
                    client.idp_sso_url = location
                    break

        key_desc = sso_desc.find(f".//{{{NSMAP['md']}}}KeyDescriptor[@use='signing']")
        if key_desc is None:
            key_desc = sso_desc.find(f".//{{{NSMAP['md']}}}KeyDescriptor")
        if key_desc is not None:
            cert_el = key_desc.find(f".//{{{NSMAP['ds']}}}X509Certificate")
            if cert_el is not None and cert_el.text:
                pem = (
                    "-----BEGIN CERTIFICATE-----\n"
                    + cert_el.text.strip()
                    + "\n-----END CERTIFICATE-----"
                )
                client.idp_cert_pem = pem


def extract_saml_claims(auth_data: dict) -> dict[str, str]:
    """Normalize SAML assertion to standard (sub, email, name) fields."""
    name_id = auth_data.get("name_id", "")
    attributes = auth_data.get("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}

    email = ""
    name = ""
    for attr_name, attr_values in attributes.items():
        if isinstance(attr_values, list) and attr_values:
            value = attr_values[0]
        else:
            value = str(attr_values)
        attr_lower = attr_name.lower()
        if attr_lower in ("email", "mail", "emailaddress"):
            email = value
        elif attr_lower in ("displayname", "name", "cn", "commonname"):
            name = value

    return {
        "sub": name_id,
        "email": email,
        "name": name or email,
    }
