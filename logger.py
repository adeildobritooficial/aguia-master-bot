# logger.py

from datetime import datetime


def log_event(event_type: str, message: str, data: dict | None = None) -> None:
    """
    Registra eventos do robô no terminal.
    Nesta primeira fase, não grava em banco de dados.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n" + "=" * 80)
    print(f"[{timestamp}] {event_type}")
    print("-" * 80)
    print(message)

    if data:
        print("\nDADOS:")
        for key, value in data.items():
            print(f"- {key}: {value}")

    print("=" * 80 + "\n")