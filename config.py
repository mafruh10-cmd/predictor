from datetime import datetime, timedelta

SEARCH_KEYWORDS_EN = [
    "rape",
    "gang rape",
    "sexual assault",
    "rape case",
    "rape victim",
    "rape accused",
]

SEARCH_KEYWORDS_BN = [
    "ধর্ষণ",       # rape
    "গণধর্ষণ",     # gang rape
    "যৌন নিপীড়ন",  # sexual assault
]

START_DATE = datetime(2015, 1, 1)
END_DATE   = datetime(2025, 12, 31)

# All 64 Bangladesh districts
DISTRICTS = [
    "Bagerhat", "Bandarban", "Barguna", "Barisal", "Bhola", "Bogura",
    "Brahmanbaria", "Chandpur", "Chapai Nawabganj", "Chattogram", "Chittagong",
    "Chuadanga", "Comilla", "Cox's Bazar", "Coxs Bazar", "Dhaka", "Dinajpur",
    "Faridpur", "Feni", "Gaibandha", "Gazipur", "Gopalganj", "Habiganj",
    "Hobiganj", "Jamalpur", "Jashore", "Jessore", "Jhalokati", "Jhenaidah",
    "Joypurhat", "Khagrachhari", "Khulna", "Kishoreganj", "Kurigram",
    "Kushtia", "Lakshmipur", "Lalmonirhat", "Madaripur", "Magura", "Manikganj",
    "Meherpur", "Moulvibazar", "Munshiganj", "Mymensingh", "Naogaon", "Narail",
    "Narayanganj", "Narsingdi", "Natore", "Netrokona", "Nilphamari",
    "Noakhali", "Pabna", "Panchagarh", "Patuakhali", "Pirojpur", "Rajbari",
    "Rajshahi", "Rangamati", "Rangpur", "Satkhira", "Shariatpur", "Sherpur",
    "Sirajganj", "Sunamganj", "Sylhet", "Tangail", "Thakurgaon",
]

PERPETRATOR_TYPES = {
    "neighbor":    ["neighbor", "neighbour", "next door"],
    "teacher":     ["teacher", "school teacher", "madrasa teacher", "madrassa", "instructor"],
    "relative":    ["relative", "uncle", "cousin", "brother-in-law", "father-in-law",
                    "stepfather", "step-father", "family member"],
    "employer":    ["employer", "boss", "landlord", "owner"],
    "colleague":   ["colleague", "co-worker", "coworker", "classmate", "fellow student"],
    "stranger":    ["stranger", "unknown", "unidentified"],
    "intimate":    ["boyfriend", "ex-boyfriend", "husband", "ex-husband", "partner"],
    "authority":   ["police", "army", "official", "politician", "councillor", "member"],
}

REQUEST_DELAY_SECONDS = 3      # polite crawl delay
MAX_RETRIES           = 3
REQUEST_TIMEOUT       = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; BangladeshRapePredictor-Research/1.0; "
    "+https://github.com/mafruh10-cmd/predictor)"
)

DB_PATH  = "data/articles.db"
CSV_PATH = "data/cases.csv"
