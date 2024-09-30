def get_float(value) -> float:
   try:
      return float(value) if value else 0
   except ValueError:
      return 0
