"""Optional neural brightness adaptation."""

from .config import load_default_config


def naka_rushton_response(retinal_illuminance_td, semi_saturation_td=None, exponent=None, config=None):
    config = config or load_default_config()
    semi_saturation_td = semi_saturation_td or config.adaptation.semi_saturation_trolands
    exponent = exponent or config.adaptation.exponent
    numerator = retinal_illuminance_td ** exponent
    denominator = numerator + semi_saturation_td ** exponent
    if denominator <= 0:
        return 0.0
    return config.adaptation.r_max * numerator / denominator


def adaptation_state(retinal_illuminance_td, enabled=True, config=None):
    config = config or load_default_config()
    if not enabled:
        return {
            "enabled": False,
            "brightness_response": retinal_illuminance_td,
            "normalized_response": 1.0
        }
    response = naka_rushton_response(retinal_illuminance_td, config=config)
    return {
        "enabled": True,
        "brightness_response": response,
        "normalized_response": response / max(config.adaptation.r_max, 1e-9)
    }
