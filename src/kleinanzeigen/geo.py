"""Geo-Funktionen — ACHTUNG: Alias-Modul, wird bald entfernt.

Bitte importiere aus .text_utils statt aus .geo.
Wird hier nur noch als Rückwärtskompatibilität re-exportiert.
"""
from .text_utils import extract_plz_from_text, parse_price

__all__ = ['extract_plz_from_text', 'parse_price']
