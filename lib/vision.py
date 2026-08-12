"""
lib/vision.py — Extract payment data from WavePay, KBZPay, and NUGPay screenshots
using OCR.space API and regex parsing.
"""
import re
import requests
from lib import config

def _clean_text(text: str) -> str:
    """Clean OCR text by removing extra spaces and normalizing newlines."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def _extract_amount(text: str) -> str:
    # Look for patterns like "10,000 Ks", "10,000.00 Ks", "Amount 10,000"
    amount_match = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:Ks|ks|MMK|mmk|ks\.)', text, re.IGNORECASE)
    if amount_match:
        return amount_match.group(1).replace(',', '')
    
    # Fallback to looking for numbers near "Amount" or "Total"
    amount_match = re.search(r'(?:Amount|Total|Amount\s*[(Ks)]*)\s*[:\n-]*\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
    if amount_match:
        return amount_match.group(1).replace(',', '')
    return ""

def _extract_account(text: str) -> str:
    # Extract phone numbers (09...)
    phone_match = re.search(r'(09[\d\s-]{7,10})', text)
    if phone_match:
        return phone_match.group(1).replace(' ', '').replace('-', '')
    
    # Extract NUGPay accounts (NUG...)
    nug_match = re.search(r'(NUG[\d]+)', text, re.IGNORECASE)
    if nug_match:
        return nug_match.group(1)
    
    return ""

def _extract_transaction_id(text: str) -> str:
    # Look for transaction ID patterns
    tx_match = re.search(r'(?:Transaction\s*ID|Txn\s*ID|TID|ID|Ref\s*No)\s*[:#\n-]*\s*([a-zA-Z0-9]+)', text, re.IGNORECASE)
    if tx_match:
        return tx_match.group(1)
    
    # Just look for long numeric sequences that aren't phone numbers (often TxIDs)
    tx_match = re.search(r'\b(?!09)(\d{9,15})\b', text)
    if tx_match:
        return tx_match.group(1)
    
    return ""

def _detect_payment_type(text: str) -> str:
    text_lower = text.lower()
    if 'wave' in text_lower or 'wavemoney' in text_lower or 'wave pay' in text_lower:
        return 'WavePay'
    elif 'kbz' in text_lower or 'kpay' in text_lower or 'kbzpay' in text_lower:
        return 'KBZPay'
    elif 'nug' in text_lower or 'nugpay' in text_lower:
        return 'NUGPay'
    return 'unknown'

def _detect_status(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ('success', 'successful', 'received', 'complete', 'done', 'paid')):
        return 'Success'
    elif any(k in text_lower for k in ('fail', 'reject', 'cancel', 'error', 'decline')):
        return 'Failed'
    return 'unknown'

def _error_result(msg: str) -> dict:
    return {
        "payment_type": "unknown",
        "status": "unknown",
        "amount": "",
        "from_account": "",
        "to_account": "",
        "recipient_name": "",
        "transaction_id": "",
        "date_time": "",
        "error": msg
    }

def extract_payment_info(image_bytes: bytes) -> dict:
    """
    Send screenshot to OCR.space API and extract payment fields via regex.
    """
    try:
        # Call OCR.space API
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': ('receipt.jpg', image_bytes, 'image/jpeg')},
            data={
                'apikey': config.OCR_SPACE_API_KEY,
                'language': 'eng',
                'isOverlayRequired': False
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            error_msgs = result.get('ErrorMessage', ['Unknown OCR error'])
            return _error_result(f"OCR API Error: {', '.join(error_msgs)}")
        
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return _error_result("OCR API returned no text")
            
        raw_text = parsed_results[0].get('ParsedText', '')
        clean_text_str = _clean_text(raw_text)
        print(f"[vision] OCR Text: {clean_text_str[:200]}...")
        
        # Regex parsing
        payment_type = _detect_payment_type(clean_text_str)
        status = _detect_status(clean_text_str)
        amount = _extract_amount(clean_text_str)
        account = _extract_account(clean_text_str)
        tx_id = _extract_transaction_id(clean_text_str)
        
        return {
            "payment_type": payment_type,
            "status": status,
            "amount": amount,
            "from_account": account, 
            "to_account": "",
            "recipient_name": "",
            "transaction_id": tx_id,
            "date_time": ""
        }

    except requests.exceptions.RequestException as e:
        return _error_result(f"OCR API Request failed: {e}")
    except Exception as e:
        return _error_result(f"Vision processing failed: {e}")
