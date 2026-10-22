from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()

ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS"]


def redact(text: str) -> str:
    results = _analyzer.analyze(text=text, entities=ENTITIES, language="en")
    return _anonymizer.anonymize(text=text, analyzer_results=results).text
