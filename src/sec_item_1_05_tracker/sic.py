"""SIC (Standard Industrial Classification) code labels.

Expanded coverage of the industries that show up most in Item 1.05
filings. The SEC Division of Corporation Finance maintains the
canonical list; this is the practical subset for cybersecurity
disclosure analysis.
"""
from __future__ import annotations

SIC_LABELS: dict[str, str] = {
    # Agriculture, Forestry, Fishing (01-09)
    "0100": "Agricultural Production - Crops",
    "0200": "Agricultural Production - Livestock",
    # Mining (10-14)
    "1040": "Gold Mining",
    "1311": "Crude Petroleum & Natural Gas",
    "1381": "Services - Oil & Gas Field Services",
    "1400": "Mining & Quarrying of Nonmetallic Minerals",
    # Construction (15-17)
    "1540": "General Building Contractors - Nonresidential",
    "1623": "Water, Sewer & Utility Lines",
    # Food & Beverage (20)
    "2000": "Food & Kindred Products",
    "2030": "Canned, Frozen & Preserved Foods",
    "2050": "Bakery Products",
    "2080": "Beverages",
    # Tobacco (21)
    "2100": "Tobacco Products",
    # Textile (22-23)
    "2200": "Textile Mill Products",
    "2300": "Apparel & Other Finished Products",
    # Paper & Publishing (24-27)
    "2400": "Lumber & Wood Products",
    "2500": "Furniture & Fixtures",
    "2600": "Paper & Allied Products",
    "2700": "Printing, Publishing & Allied Industries",
    "2711": "Newspapers Publishing",
    "2721": "Periodical Publishing",
    "2731": "Book Publishing",
    # Chemicals (28)
    "2800": "Chemicals & Allied Products",
    "2834": "Pharmaceutical Preparations",
    "2836": "Biological Products",
    # Petroleum (29)
    "2911": "Petroleum Refining",
    # Rubber & Plastic (30)
    "3089": "Plastics Products",
    # Leather (31)
    "3100": "Leather & Leather Products",
    # Stone, Clay, Glass (32)
    "3211": "Flat Glass",
    # Primary Metal (33)
    "3310": "Steel Works & Blast Furnaces",
    # Fabricated Metal (34)
    "3400": "Fabricated Metal Products",
    # Industrial Machinery (35)
    "3500": "Industrial & Commercial Machinery",
    "3559": "Special Industry Machinery",
    "3569": "General Industrial Machinery",
    "3571": "Electronic Computers",
    "3572": "Computer Storage Devices",
    "3576": "Computer Communications Equipment",
    "3577": "Computer Peripheral Equipment",
    # Electronic (36)
    "3600": "Electronic & Other Electrical Equipment",
    "3651": "Household Audio & Video Equipment",
    "3661": "Telephone & Telegraph Apparatus",
    "3663": "Radio & TV Broadcasting & Communications Equipment",
    "3669": "Communications Equipment, NEC",
    "3672": "Printed Circuit Boards",
    "3674": "Semiconductors & Related Devices",
    "3678": "Electronic Connectors",
    "3690": "Electric Industrial Apparatus, NEC",
    # Transportation (37)
    "3711": "Motor Vehicles",
    "3713": "Truck & Bus Bodies",
    "3714": "Motor Vehicle Parts",
    "3721": "Aircraft",
    "3724": "Aircraft Engines & Engine Parts",
    "3728": "Aircraft Parts & Auxiliary Equipment",
    "3730": "Ship & Boat Building & Repair",
    "3760": "Guided Missiles & Space Vehicles",
    "3812": "Search, Detection, Navigation, Guidance",
    # Instruments (38)
    "3825": "Industrial Instruments",
    "3827": "Optical Instruments & Lenses",
    "3841": "Surgical & Medical Instruments",
    "3842": "Orthopedic, Prosthetic & Surgical Appliances",
    "3844": "X-Ray Apparatus & Tubes",
    "3845": "Electromedical & Electrotherapeutic Apparatus",
    "3861": "Photographic Equipment",
    "3873": "Watches, Clocks, Clockwork Operated Devices",
    # Transportation Services (40-49)
    "4011": "Railroads - Line Haul",
    "4213": "Trucking",
    "4412": "Deep Sea Transportation",
    "4512": "Air Transportation - Scheduled",
    "4522": "Air Transportation - Nonscheduled",
    # Utilities (49)
    "4812": "Radiotelephone Communications",
    "4813": "Telephone Communications (No Radio)",
    "4822": "Telegraph & Other Message Communications",
    "4833": "Television Broadcasting Stations",
    "4899": "Communications Services, NEC",
    "4900": "Electric, Gas, Water & Sanitary Services",
    "4911": "Electric Services",
    "4922": "Natural Gas Transmission",
    "4931": "Electric & Other Services Combined",
    "4941": "Water Supply",
    "4953": "Refuse Systems",
    # Wholesale (50-51)
    "5000": "Wholesale - Durable Goods",
    "5040": "Wholesale - Professional & Commercial Equipment",
    "5065": "Wholesale - Electronic Parts",
    "5080": "Wholesale - Machinery, Equipment & Supplies",
    "5141": "Wholesale - Groceries",
    # Retail (52-59)
    "5200": "Retail - Building Materials",
    "5211": "Retail - Lumber & Building Materials",
    "5311": "Retail - Department Stores",
    "5411": "Grocery Stores",
    "5500": "Retail - Auto Dealers & Gasoline Stations",
    "5621": "Retail - Women's Clothing Stores",
    "5651": "Retail - Family Clothing Stores",
    "5712": "Retail - Furniture Stores",
    "5734": "Computer & Computer Software Stores",
    "5812": "Eating Places",
    "5912": "Drug Stores & Proprietary Stores",
    "5940": "Retail - Miscellaneous Shopping Goods",
    "5961": "Catalog, Mail-Order Houses",
    "5990": "Retail - Miscellaneous, NEC",
    # Finance (60-67)
    "6020": "State Commercial Banks",
    "6021": "National Commercial Banks",
    "6022": "State Commercial Banks",
    "6029": "Commercial Banks, NEC",
    "6035": "Savings Institution, Federally Chartered",
    "6036": "Savings Institution, State Chartered",
    "6099": "Functions Related to Depository Banking",
    "6141": "Personal Credit Institutions",
    "6150": "Short-Term Business Credit Institutions",
    "6159": "Federal & Federally-Sponsored Credit Agencies",
    "6162": "Mortgage Bankers & Loan Correspondents",
    "6172": "Finance Services",
    "6189": "Asset-Backed Securities",
    "6199": "Finance Services",
    "6200": "Security & Commodity Brokers",
    "6211": "Security Brokers, Dealers & Flotation Companies",
    "6221": "Commodity Contracts Brokers & Dealers",
    "6282": "Investment Advice",
    "6311": "Life Insurance",
    "6321": "Accident & Health Insurance",
    "6331": "Fire, Marine & Casualty Insurance",
    "6400": "Insurance Agents, Brokers & Service",
    "6500": "Real Estate",
    "6512": "Operators of Apartment Buildings",
    "6552": "Land Subdividers & Developers",
    "6770": "Blank Checks",
    "6798": "Real Estate Investment Trusts",
    "6770": "Blank Checks (Shell Companies)",
    # Services (70-89)
    "7011": "Hotels & Motels",
    "7200": "Services - Personal",
    "7311": "Services - Advertising",
    "7322": "Services - Adjustment & Collection Services",
    "7340": "Services - Services To Dwellings & Other Buildings",
    "7359": "Services - Equipment Rental & Leasing, NEC",
    "7361": "Services - Employment Agencies",
    "7363": "Services - Help Supply Services",
    "7370": "Services - Computer Services",
    "7371": "Services - Computer Programming",
    "7372": "Services - Prepackaged Software",
    "7373": "Services - Computer Integrated Systems Design",
    "7374": "Services - Computer Processing & Data Preparation",
    "7377": "Services - Computer Rental & Leasing",
    "7380": "Services - Miscellaneous Business Services",
    "7381": "Services - Detective, Guard & Armored Car Services",
    "7389": "Services - Business Services, NEC",
    "7510": "Services - Automotive Services",
    "7812": "Services - Motion Picture & Video Production",
    "7819": "Services - Allied to Motion Pictures",
    "7822": "Services - Motion Picture Distribution",
    "7829": "Services - Allied to Motion Picture Distribution",
    "7830": "Services - Motion Picture Theaters",
    "7948": "Services - Racing, Including Track Operation",
    "7990": "Services - Amusement & Recreation Services",
    "7993": "Services - Patent Owners & Lessors",
    "7997": "Services - Membership Sports & Recreation Clubs",
    "8000": "Services - Health Services",
    "8011": "Services - Offices of Doctors of Medicine",
    "8050": "Services - Nursing & Personal Care Facilities",
    "8060": "Services - Hospitals",
    "8062": "Services - General Medical & Surgical Hospitals",
    "8071": "Services - Medical Laboratories",
    "8082": "Services - Home Health Care Services",
    "8090": "Services - Health Services, NEC",
    "8093": "Services - Specialty Outpatient Facilities, NEC",
    "8100": "Services - Legal Services",
    "8200": "Services - Educational Services",
    "8300": "Services - Social Services",
    "8351": "Services - Child Day Care Services",
    "8600": "Services - Membership Organizations",
    "8711": "Services - Engineering Services",
    "8731": "Services - Commercial Physical & Biological Research",
    "8734": "Services - Testing Laboratories",
    "8741": "Services - Management Services",
    "8742": "Services - Management Consulting Services",
    "8744": "Services - Facilities Support Management Services",
    "8880": "Services - American Depositary Receipts",
    "8888": "Foreign Governments",
    "8900": "Services - Services, NEC",
    # Public Administration (91-99)
    "9995": "Non-Classifiable Establishments",
}


def sic_label(sic: str) -> str:
    """Return the canonical label for a SIC code, or '' if unknown."""
    return SIC_LABELS.get((sic or "").strip(), "")


def sic_sector(sic: str) -> str:
    """Return the high-level sector name for a SIC code."""
    if not sic:
        return ""
    try:
        n = int(sic[:2])
    except Exception:
        return ""
    if n <= 9: return "Agriculture"
    if n <= 14: return "Mining"
    if n <= 17: return "Construction"
    if n <= 39: return "Manufacturing"
    if n <= 49: return "Transportation & Utilities"
    if n <= 51: return "Wholesale Trade"
    if n <= 59: return "Retail Trade"
    if n <= 67: return "Finance, Insurance & Real Estate"
    if n <= 89: return "Services"
    if n <= 99: return "Public Administration"
    return ""
