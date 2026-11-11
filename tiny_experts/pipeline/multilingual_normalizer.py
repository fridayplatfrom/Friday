import re
from typing import Dict, Any, List, Optional, Tuple

class MultilingualVernacularNormalizer:
    """
    Multilingual Vernacular Agricultural Engine.
    Enables farmers and agronomists across India and South Asia to query the system in:
    - Hindi (हिन्दी)
    - Punjabi (ਪੰਜਾਬੀ)
    - Telugu (తెలుగు)
    - Tamil (தமிழ்)
    - Marathi (मराठी)
    and their Romanized/transliterated equivalents (e.g. 'jhulsa', 'kungi', 'karpa', 'budida').

    Autonomously detects script/language, extracts vernacular symptoms and crops,
    normalizes the query for neural and BM25 routing, and provides localized advice.
    """

    # Unicode script ranges
    SCRIPTS = {
        "Devanagari": (0x0900, 0x097F),
        "Gurmukhi":   (0x0A00, 0x0A7F),
        "Tamil":      (0x0B80, 0x0BFF),
        "Telugu":     (0x0C00, 0x0C7F)
    }

    # Crop Translations
    CROPS = {
        # Hindi / Marathi
        "टमाटर": "tomato", "आलू": "potato", "धान": "rice", "चावल": "rice",
        "गन्ना": "sugarcane", "कपास": "cotton", "गेहूं": "wheat", "मिर्च": "chilli",
        "सरसों": "mustard", "चना": "chickpea", "अरहर": "pigeonpea", "नींबू": "citrus",
        "अंगूर": "grape", "केला": "banana", "आम": "mango", "बैंगन": "eggplant",
        "कांदा": "onion", "सोयाबीन": "soybean",
        # Punjabi
        "ਟਮਾਟਰ": "tomato", "ਆਲੂ": "potato", "ਝੋਨਾ": "rice", "ਚਾਵਲ": "rice",
        "ਗੰਨਾ": "sugarcane", "ਕਪਾਹ": "cotton", "ਨਰਮਾ": "cotton", "ਕਣਕ": "wheat",
        "ਮਿਰਚ": "chilli", "ਸਰ੍ਹੋਂ": "mustard", "ਛੋਲੇ": "chickpea",
        # Telugu
        "టమోటా": "tomato", "బంగాళాదుంప": "potato", "వరి": "rice",
        "చెరకు": "sugarcane", "ప్రత్తి": "cotton", "గోధుమ": "wheat", "మిరప": "chilli",
        "నిమ్మ": "citrus", "ద్రాక్ష": "grape", "అరటి": "banana",
        # Tamil
        "தக்காளி": "tomato", "தக்காளியில்": "tomato", "உருளைக்கிழங்கு": "potato", "நெல்": "rice", "நெல்லில்": "rice",
        "கரும்பு": "sugarcane", "கரும்பில்": "sugarcane", "பருத்தி": "cotton", "பருத்தியில்": "cotton",
        "கோதுமை": "wheat", "மிளகாய்": "chilli",
        "எலுமிச்சை": "citrus", "திராட்சை": "grape", "வாழை": "banana"
    }

    # Disease Dictionaries
    DISEASES = {
        # Hindi
        "अगेती झुलसा": ("Early Blight", "Alternaria solani", "hi"),
        "पछेती झुलसा": ("Late Blight", "Phytophthora infestans", "hi"),
        "झुलसा": ("Early Blight", "Alternaria solani", "hi"),
        "सफेद चूर्णी": ("Powdery Mildew", "Podosphaera xanthii", "hi"),
        "चूर्णी फफूंद": ("Powdery Mildew", "Podosphaera xanthii", "hi"),
        "उकठा": ("Fusarium Wilt", "Fusarium oxysporum", "hi"),
        "सूखा रोग": ("Fusarium Wilt", "Fusarium oxysporum", "hi"),
        "लाल सड़न": ("Sugarcane Red Rot", "Colletotrichum falcatum", "hi"),
        "जीवाणु झुलसा": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "hi"),
        "जीवाणु अंगमारी": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "hi"),
        "पत्ती मरोड़": ("Tomato Yellow Leaf Curl", "TYLCV", "hi"),
        "मृदुरोमिल": ("Downy Mildew", "Pseudoperonospora cubensis", "hi"),
        "जड़ गांठ": ("Root-Knot Nematode", "Meloidogyne incognita", "hi"),
        "गेरुआ": ("Black Stem Rust", "Puccinia graminis", "hi"),
        "किट्ट": ("Black Stem Rust", "Puccinia graminis", "hi"),

        # Punjabi
        "ਅਗੇਤਾ ਝੁਲਸਾ": ("Early Blight", "Alternaria solani", "pa"),
        "ਪਛੇਤਾ ਝੁਲਸਾ": ("Late Blight", "Phytophthora infestans", "pa"),
        "ਕੁੰਗੀ": ("Black Stem Rust", "Puccinia graminis", "pa"),
        "ਚਿੱਟਾ ਰੋਗ": ("Powdery Mildew", "Podosphaera xanthii", "pa"),
        "ਝੁਲਸ": ("Early Blight", "Alternaria solani", "pa"),
        "ਕਪਾਹ ਦਾ ਪੱਤਾ ਮਰੋੜ": ("Cotton Leaf Curl", "CLCuV", "pa"),
        "ਸੜਾਂਦ": ("Bacterial Soft Rot", "Pectobacterium carotovorum", "pa"),

        # Telugu
        "ఎండ్ర తెగులు": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "te"),
        "అగ్గి తెగులు": ("Early Blight", "Alternaria solani", "te"),
        "బూడిద తెగులు": ("Powdery Mildew", "Podosphaera xanthii", "te"),
        "ఎర్ర కుళ్లు തെగులు": ("Sugarcane Red Rot", "Colletotrichum falcatum", "te"),
        "ఎర్ర కుళ్లు": ("Sugarcane Red Rot", "Colletotrichum falcatum", "te"),
        "ఆకు ముడత": ("Tomato Yellow Leaf Curl", "TYLCV", "te"),
        "వేరు కుళ్లు": ("Root-Knot Nematode", "Meloidogyne incognita", "te"),

        # Tamil
        "குலை நோய்": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "ta"),
        "சாம்பல் நோய்": ("Powdery Mildew", "Podosphaera xanthii", "ta"),
        "செவ்வழுகல் நோய்": ("Sugarcane Red Rot", "Colletotrichum falcatum", "ta"),
        "செவ்வழுகல்": ("Sugarcane Red Rot", "Colletotrichum falcatum", "ta"),
        "இலைச் சுருள் நோய்": ("Tomato Yellow Leaf Curl", "TYLCV", "ta"),
        "இலைச் சுருள்": ("Tomato Yellow Leaf Curl", "TYLCV", "ta"),
        "வேர் முடிச்சு": ("Root-Knot Nematode", "Meloidogyne incognita", "ta"),
        "வாடல் நோய்": ("Fusarium Wilt", "Fusarium oxysporum", "ta"),

        # Marathi
        "करपा": ("Early Blight", "Alternaria solani", "mr"),
        "भुरी": ("Powdery Mildew", "Podosphaera xanthii", "mr"),
        "भुरी रोग": ("Powdery Mildew", "Podosphaera xanthii", "mr"),
        "तांबेरा": ("Black Stem Rust", "Puccinia graminis", "mr"),
        "लाल कूज": ("Sugarcane Red Rot", "Colletotrichum falcatum", "mr"),
        "केवडा": ("Downy Mildew", "Pseudoperonospora cubensis", "mr"),

        # Transliterated Romanized Terms
        "jhulsa": ("Early Blight", "Alternaria solani", "hi"),
        "ageti jhulsa": ("Early Blight", "Alternaria solani", "hi"),
        "pacheti jhulsa": ("Late Blight", "Phytophthora infestans", "hi"),
        "uktha": ("Fusarium Wilt", "Fusarium oxysporum", "hi"),
        "sukha rog": ("Fusarium Wilt", "Fusarium oxysporum", "hi"),
        "lal sadan": ("Sugarcane Red Rot", "Colletotrichum falcatum", "hi"),
        "bhoori": ("Powdery Mildew", "Podosphaera xanthii", "hi"),
        "bhuri": ("Powdery Mildew", "Podosphaera xanthii", "mr"),
        "karpa": ("Early Blight", "Alternaria solani", "mr"),
        "kungi": ("Black Stem Rust", "Puccinia graminis", "pa"),
        "endra tegulu": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "te"),
        "budida tegulu": ("Powdery Mildew", "Podosphaera xanthii", "te"),
        "aggi tegulu": ("Early Blight", "Alternaria solani", "te"),
        "erra kullu": ("Sugarcane Red Rot", "Colletotrichum falcatum", "te"),
        "kulaiknoi": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "ta"),
        "kulai noi": ("Rice Bacterial Leaf Blight", "Xanthomonas oryzae", "ta"),
        "sambal noi": ("Powdery Mildew", "Podosphaera xanthii", "ta"),
        "sevvalukal": ("Sugarcane Red Rot", "Colletotrichum falcatum", "ta")
    }

    LOCALIZED_TEMPLATES = {
        "hi": "रोग निदान: {disease} ({pathogen})। उपचार: {treatment}।",
        "pa": "ਬਿਮਾਰੀ ਦੀ ਜਾਂਚ: {disease} ({pathogen})। ਇਲਾਜ: {treatment}।",
        "te": "వ్యాధి నిర్ధారణ: {disease} ({pathogen})। నివారణ: {treatment}।",
        "ta": "நோய் கண்டறிதல்: {disease} ({pathogen})। சிகிச்சை: {treatment}।",
        "mr": "रोग निदान: {disease} ({pathogen})। उपाययोजना: {treatment}।"
    }

    @classmethod
    def detect_script_or_language(cls, text: str) -> str:
        """Determines the script or regional language of input text."""
        for char in text:
            cp = ord(char)
            if 0x0A00 <= cp <= 0x0A7F:
                return "pa" # Punjabi / Gurmukhi
            if 0x0C00 <= cp <= 0x0C7F:
                return "te" # Telugu
            if 0x0B80 <= cp <= 0x0BFF:
                return "ta" # Tamil
            if 0x0900 <= cp <= 0x097F:
                # Distinguish Marathi vs Hindi by specific vocabulary
                if any(w in text for w in ["करपा", "भुरी", "तांबेरा", "आहे", "झाले", "करावे"]):
                    return "mr"
                return "hi" # Hindi / Devanagari

        # Romanized keyword check
        text_lower = text.lower()
        if any(w in text_lower for w in ["kungi", "chitta"]):
            return "pa"
        if any(w in text_lower for w in ["tegulu", "kullu", "aaku"]):
            return "te"
        if any(w in text_lower for w in ["noi", "sevvalukal", "kulai"]):
            return "ta"
        if any(w in text_lower for w in ["karpa", "bhuri", "tambera"]):
            return "mr"
        if any(w in text_lower for w in ["jhulsa", "uktha", "sadan", "rog", "tamatar", "patte"]):
            return "hi"

        return "en"

    @classmethod
    def normalize(cls, query: str) -> Dict[str, Any]:
        """
        Parses vernacular input, maps regional crop & disease terms to canonical English,
        and provides full normalized routing parameters.
        """
        lang = cls.detect_script_or_language(query)
        detected_crops = []
        detected_diseases = []
        matched_vernacular_phrases = []

        # 1. Match crops
        for vern_crop, eng_crop in cls.CROPS.items():
            if vern_crop in query:
                detected_crops.append(eng_crop)
                matched_vernacular_phrases.append(vern_crop)

        # 2. Match diseases (longer matches first to avoid prefix collisions)
        sorted_diseases = sorted(cls.DISEASES.items(), key=lambda x: len(x[0]), reverse=True)
        for vern_term, (eng_disease, pathogen, term_lang) in sorted_diseases:
            if vern_term in query or vern_term.lower() in query.lower():
                if not any(eng_disease == d["disease"] for d in detected_diseases):
                    detected_diseases.append({
                        "disease": eng_disease,
                        "pathogen": pathogen,
                        "vernacular_name": vern_term
                    })
                    matched_vernacular_phrases.append(vern_term)
                    if lang == "en":
                        lang = term_lang

        # 3. Formulate normalized clinical query
        parts = []
        if detected_crops:
            parts.append(f"Crop: {' '.join(detected_crops)}")
        if detected_diseases:
            d_names = [d["disease"] for d in detected_diseases]
            parts.append(f"Condition: {' '.join(d_names)}")
        else:
            # Fallback transliteration
            parts.append(query)

        normalized_query_str = f"{query} [Normalized: {' | '.join(parts)}]" if parts else query

        return {
            "original_query": query,
            "detected_language": lang,
            "is_vernacular": lang != "en",
            "matched_vernacular_phrases": matched_vernacular_phrases,
            "detected_crops": list(set(detected_crops)),
            "detected_diseases": detected_diseases,
            "canonical_disease": detected_diseases[0]["disease"] if detected_diseases else None,
            "canonical_pathogen": detected_diseases[0]["pathogen"] if detected_diseases else None,
            "normalized_query": normalized_query_str
        }

    @classmethod
    def get_localized_advisory(cls, lang: str, disease: str, pathogen: str, treatment: str) -> Optional[str]:
        """Builds a regional advisory string in farmer's native language."""
        if lang not in cls.LOCALIZED_TEMPLATES:
            return None
        template = cls.LOCALIZED_TEMPLATES[lang]
        # Shorten treatment if too long
        short_tx = treatment.split(";")[0] if ";" in treatment else treatment[:80]
        return template.format(disease=disease, pathogen=pathogen, treatment=short_tx)
