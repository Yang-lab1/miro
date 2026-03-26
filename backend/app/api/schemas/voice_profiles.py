from app.api.schemas.common import StrictModel


class VoiceProfileResponseItem(StrictModel):
    voiceProfileId: str
    providerVoiceId: str
    countryKey: str
    gender: str
    locale: str
    displayName: str
