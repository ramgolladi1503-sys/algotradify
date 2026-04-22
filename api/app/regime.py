def detect_regime(adx, compression):
    if adx > 25:
        return "trending"
    if compression > 0.7:
        return "sideways"
    return "volatile"
