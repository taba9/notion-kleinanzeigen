"""Zentrales Logging-Modul für den Kleinanzeigen-Workflow.

Bietet einheitliche, zeitgestempelte Log-Ausgaben.
Kann je nach Kontext (Terminal vs. Cron) konfiguriert werden.
"""

import sys
import time


def log(msg, prefix=''):
    """Einheitliche Log-Ausgabe mit Zeitstempel.

    Args:
        msg: Die Nachricht
        prefix: Optionaler Prefix (z.B. '  ', '⚠ ')
    """
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {prefix}{msg}')
    sys.stdout.flush()


def section(title):
    """Loggt einen Abschnittstitel mit optischer Hervorhebung."""
    log('')
    log('─' * 55)
    log(f' {title}')
    log('─' * 55)


def header(title):
    """Loggt einen grossen Header."""
    log('')
    log('═' * 55)
    log(f' {title}')
    log('═' * 55)


def summary_line(label, value, icon=''):
    """Einzeilige Zusammenfassung."""
    log(f'  {icon} {label}: {value}')
