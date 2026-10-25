from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()

ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS"]


def redact(text: str) -> str:
    results = _analyzer.analyze(text=text, entities=ENTITIES, language="en")
    return _anonymizer.anonymize(text=text, analyzer_results=results).text

# # TEMPORARY STUB to bypass Python 3.14 spaCy crash
# import structlog
# log = structlog.get_logger()

# def redact(text: str) -> str:
#     """Temporarily returns text unchanged to bypass spaCy crash."""
#     log.warning("PII_REDACTION_BYPASSED")
#     return text