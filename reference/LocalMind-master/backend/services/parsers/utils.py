import logging
import re

logger = logging.getLogger(__name__)

def is_readable_text(text: str) -> bool:
    """Check if the extracted text looks like readable content and not OCR garbage."""
    if len(text.strip()) < 50:
        return False
    words = text.split()
    if len(words) < 10:
        return False
        
    # Count words that look like real English words
    # (mostly letters, length 2-20, no weird symbols)
    real_words = [
        w for w in words
        if re.match(r'^[a-zA-Z]{2,20}$', w.strip('.,;:()[]'))
    ]
    ratio = len(real_words) / len(words)
    
    # Reject if less than 40% of words look like real words
    if ratio < 0.4:
        logger.debug(f"[FILTER] Rejected OCR garbage chunk: ratio={ratio:.2f} sample={text[:80]}")
        return False
    return True
