"""
Fact Guard module for checking and correcting factual information
Provides pre-defined responses for common factual queries
"""

import re
from typing import Optional, Tuple


class FactGuard:
    """
    Fact checking system with pre-defined accurate responses
    """

    def __init__(self):
        self.fact_db = {
            # Scientific facts
            "speed of light": ("The speed of light in vacuum is 299,792,458 meters per second (approximately 300,000 km/s or 186,282 miles per second).", "science"),
            "earth radius": ("Earth's mean radius is approximately 6,371 kilometers (3,959 miles).", "science"),
            "gravity acceleration": ("Standard gravity on Earth is approximately 9.81 m/s² (32.2 ft/s²).", "science"),
            "water boiling point": ("Water boils at 100°C (212°F) at standard atmospheric pressure (1 atm).", "science"),
            "water freezing point": ("Water freezes at 0°C (32°F) at standard atmospheric pressure.", "science"),

            # Mathematical facts
            "pi value": ("Pi (π) is approximately 3.14159265359, an irrational number representing the ratio of a circle's circumference to its diameter.", "math"),
            "euler number": ("Euler's number (e) is approximately 2.71828182846, the base of natural logarithms.", "math"),
            "golden ratio": ("The golden ratio (φ) is approximately 1.61803398875, often found in nature and art.", "math"),

            # Historical facts
            "world war 2 end": ("World War II ended in 1945: May 8, 1945 in Europe (V-E Day) and September 2, 1945 in Asia (V-J Day).", "history"),
            "world war 1 end": ("World War I ended on November 11, 1918 with the Armistice.", "history"),
            "moon landing": ("The first Moon landing occurred on July 20, 1969 during the Apollo 11 mission. Neil Armstrong and Buzz Aldrin were the first humans to walk on the Moon.", "history"),

            # Astronomical facts
            "planets in solar system": ("There are 8 planets in our solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Pluto was reclassified as a dwarf planet in 2006.", "astronomy"),
            "sun distance": ("The average distance from Earth to the Sun is approximately 149.6 million kilometers (93 million miles), defined as 1 Astronomical Unit (AU).", "astronomy"),
            "moon distance": ("The average distance from Earth to the Moon is approximately 384,400 kilometers (238,855 miles).", "astronomy"),

            # Programming facts
            "python created": ("Python was created by Guido van Rossum and first released in 1991.", "programming"),
            "first programming language": ("The first high-level programming language was Plankalkül, designed by Konrad Zuse in the 1940s. FORTRAN (1957) was the first widely used high-level language.", "programming"),

            # Geography facts
            "highest mountain": ("Mount Everest is the highest mountain on Earth, standing at 8,848.86 meters (29,031.7 feet) above sea level.", "geography"),
            "deepest ocean": ("The Mariana Trench in the Pacific Ocean is the deepest part of Earth's oceans, reaching approximately 11,034 meters (36,201 feet) at Challenger Deep.", "geography"),
            "largest ocean": ("The Pacific Ocean is the largest ocean, covering approximately 165.2 million square kilometers.", "geography"),

            # Biology facts
            "human chromosomes": ("Humans typically have 46 chromosomes (23 pairs) in each cell, except for reproductive cells which have 23.", "biology"),
            "dna structure": ("DNA has a double helix structure, discovered by James Watson and Francis Crick in 1953 (with crucial contributions from Rosalind Franklin).", "biology"),

            # Technology facts
            "first computer": ("The first electronic general-purpose computer was ENIAC (Electronic Numerical Integrator and Computer), completed in 1945.", "technology"),
            "internet created": ("The Internet evolved from ARPANET, which was launched in 1969. The World Wide Web was invented by Tim Berners-Lee in 1989.", "technology"),
        }

        # Compile patterns for faster matching
        self.patterns = {}
        for key in self.fact_db.keys():
            # Create flexible regex pattern
            pattern = r'\b' + re.escape(key).replace(r'\ ', r'\s+') + r'\b'
            self.patterns[key] = re.compile(pattern, re.IGNORECASE)

    def check(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Check if query matches a known fact

        Args:
            query: User query to check

        Returns:
            Tuple of (response, category) if match found, None otherwise
        """
        query_lower = query.lower().strip()

        # Direct match first
        for key, (response, category) in self.fact_db.items():
            if key in query_lower:
                return (response, category)

        # Pattern match (more flexible)
        for key, pattern in self.patterns.items():
            if pattern.search(query_lower):
                response, category = self.fact_db[key]
                return (response, category)

        # Check for question patterns
        if self._is_factual_question(query_lower):
            # Try to extract the subject
            subject = self._extract_subject(query_lower)
            if subject:
                for key in self.fact_db.keys():
                    if key in subject:
                        response, category = self.fact_db[key]
                        return (response, category)

        return None

    def _is_factual_question(self, query: str) -> bool:
        """Check if query is a factual question"""
        question_patterns = [
            r'^what is',
            r'^what\'s',
            r'^how many',
            r'^how much',
            r'^when did',
            r'^when was',
            r'^where is',
            r'^who is',
            r'^who was',
            r'^tell me about',
            r'^define',
            r'^explain',
        ]

        for pattern in question_patterns:
            if re.match(pattern, query, re.IGNORECASE):
                return True

        return False

    def _extract_subject(self, query: str) -> str:
        """Extract the subject from a question"""
        # Remove question words
        subject = re.sub(r'^(what is|what\'s|how many|how much|when did|when was|where is|who is|who was|tell me about|define|explain)\s+', '', query, flags=re.IGNORECASE)

        # Remove trailing punctuation
        subject = re.sub(r'[?!.]+$', '', subject)

        return subject.strip()

    def add_fact(self, key: str, response: str, category: str = "general"):
        """
        Add a new fact to the database

        Args:
            key: Keyword or phrase to match
            response: Factual response
            category: Category of the fact
        """
        self.fact_db[key] = (response, category)

        # Update pattern
        pattern = r'\b' + re.escape(key).replace(r'\ ', r'\s+') + r'\b'
        self.patterns[key] = re.compile(pattern, re.IGNORECASE)

    def get_categories(self) -> list:
        """Get list of all fact categories"""
        categories = set()
        for _, (_, category) in self.fact_db.items():
            categories.add(category)
        return sorted(list(categories))

    def get_facts_by_category(self, category: str) -> dict:
        """Get all facts in a specific category"""
        facts = {}
        for key, (response, cat) in self.fact_db.items():
            if cat == category:
                facts[key] = response
        return facts
