SELECTORS: dict[str, str] = {
    "card": "div.row",
    "photo": "div.col-md-2.col-lg-2.cSpeakerSide.pe-0 img",
    "name": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h4",
    "designation": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h6",
    "bio": "div.cModelBio",
}

TARGET_URL = "https://wso2.com/wso2con/2026/north-america/agenda/"
OUTPUT_CSV = "output/speakers.csv"
