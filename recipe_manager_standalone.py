#!/usr/bin/env python3
"""
Recipe Manager (Standalone Version)
- Add recipes from URLs
- Add recipes manually
- Categorize recipes (meal, side, dessert, etc.)
- Generate weekly meal plans
- Create consolidated shopping lists

This is a standalone version that includes JSON-LD extraction functionality.
For the modular version, use recipe_manager.py and jsonld_extractor.py separately.
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict
import re

try:
    from recipe_scrapers import scrape_me
except ImportError:
    print("Error: recipe-scrapers not installed.")
    print("Run: pip install recipe-scrapers")
    print(f"\nPython path: {sys.executable}")
    print("\nTry one of these:")
    print("  py -m pip install recipe-scrapers")
    print("  python -m pip install recipe-scrapers")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed.")
    print(f"\nPython path: {sys.executable}")
    print("\nTry one of these:")
    print("  py -m pip install pandas")
    print("  python -m pip install pandas")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
    import requests
    JSONLD_AVAILABLE = True
except ImportError:
    print("Warning: beautifulsoup4 or requests not installed.")
    print("JSON-LD extraction will be unavailable.")
    print("Run: pip install beautifulsoup4 requests")
    JSONLD_AVAILABLE = False


# ============================================================================
# JSON-LD Recipe Extractor Functions
# ============================================================================
# Based on the approach used by obsidian-recipe-grabber:
# https://github.com/seethroughdev/obsidian-recipe-grabber

def extract_jsonld_recipes(html: str, url: str = '') -> List[Dict]:
    """
    Extract recipe data from JSON-LD structured data in HTML
    
    Args:
        html: HTML content of the page
        url: Source URL (optional)
        
    Returns:
        List of recipe dictionaries found in the page
    """
    if not JSONLD_AVAILABLE:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    recipes = []
    
    # Find all JSON-LD script tags
    jsonld_scripts = soup.find_all('script', type='application/ld+json')
    
    for script in jsonld_scripts:
        try:
            content = script.string.strip()
            if not content:
                continue
                
            data = json.loads(content)
            
            # Handle different JSON-LD formats
            schemas = []
            if isinstance(data, list):
                schemas = data
            elif isinstance(data, dict):
                if '@graph' in data and isinstance(data['@graph'], list):
                    # Handle @graph format
                    schemas = data['@graph']
                else:
                    schemas = [data]
            
            # Extract recipes from schemas
            for schema in schemas:
                recipe = _extract_recipe_from_schema(schema, url)
                if recipe:
                    recipes.append(recipe)
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Skip invalid JSON
            continue
    
    return recipes


def _extract_recipe_from_schema(schema: Dict, url: str = '') -> Optional[Dict]:
    """
    Extract recipe data from a single JSON-LD schema object
    
    Args:
        schema: JSON-LD schema object
        url: Source URL
        
    Returns:
        Recipe dictionary or None if not a recipe
    """
    # Check if this is a Recipe type
    schema_type = schema.get('@type', '')
    if isinstance(schema_type, list):
        is_recipe = 'Recipe' in schema_type
    else:
        is_recipe = schema_type == 'Recipe'
    
    if not is_recipe:
        return None
    
    recipe = {
        'title': _get_nested_value(schema, ['name', 'headline']),
        'url': url or _get_nested_value(schema, ['url']),
        'description': _get_nested_value(schema, ['description']),
        'image_url': _normalize_image(schema.get('image')),
        'cook_time': _normalize_duration(schema.get('totalTime') or schema.get('cookTime')),
        'prep_time': _normalize_duration(schema.get('prepTime')),
        'servings': _normalize_yield(schema.get('recipeYield')),
        'ingredients': _normalize_ingredients(schema.get('recipeIngredient', [])),
        'instructions': _normalize_instructions(schema.get('recipeInstructions', [])),
        'author': _get_nested_value(schema, ['author', 'name']),
        'date_published': schema.get('datePublished'),
        'cuisine': schema.get('recipeCuisine'),
        'category': schema.get('recipeCategory'),
        'keywords': schema.get('keywords'),
    }
    
    # Remove None values
    recipe = {k: v for k, v in recipe.items() if v is not None and v != ''}
    
    return recipe if recipe.get('title') else None


def _get_nested_value(obj: Dict, keys: List[str]) -> Optional[str]:
    """Get value from nested dictionary using multiple possible keys"""
    for key in keys:
        value = obj.get(key)
        if value:
            if isinstance(value, dict):
                return value.get('name') or value.get('@value') or str(value)
            elif isinstance(value, list) and len(value) > 0:
                first = value[0]
                if isinstance(first, dict):
                    return first.get('name') or first.get('@value') or str(first)
                return str(first)
            return str(value)
    return None


def _normalize_image(image: Any) -> Optional[str]:
    """Normalize image field (can be string, dict, or list)"""
    if not image:
        return None
    
    if isinstance(image, str):
        return image
    elif isinstance(image, dict):
        return image.get('url') or image.get('@id') or str(image)
    elif isinstance(image, list) and len(image) > 0:
        first = image[0]
        if isinstance(first, str):
            return first
        elif isinstance(first, dict):
            return first.get('url') or first.get('@id') or str(first)
    
    return str(image) if image else None


def _normalize_duration(duration: Any) -> Optional[str]:
    """Normalize ISO 8601 duration (PT1H30M) to readable format"""
    if not duration:
        return None
    
    if isinstance(duration, str):
        # Handle ISO 8601 duration format (PT1H30M)
        if duration.startswith('PT'):
            duration = duration[2:]  # Remove PT prefix
            hours = re.search(r'(\d+)H', duration)
            minutes = re.search(r'(\d+)M', duration)
            seconds = re.search(r'(\d+)S', duration)
            
            parts = []
            if hours:
                parts.append(f"{hours.group(1)}h")
            if minutes:
                parts.append(f"{minutes.group(1)}m")
            if seconds:
                parts.append(f"{seconds.group(1)}s")
            
            return ' '.join(parts) if parts else duration
    
    return str(duration)


def _normalize_yield(yield_value: Any) -> Optional[str]:
    """Normalize recipe yield/servings"""
    if not yield_value:
        return None
    
    if isinstance(yield_value, (int, float)):
        return str(int(yield_value))
    elif isinstance(yield_value, str):
        return yield_value
    elif isinstance(yield_value, list):
        # If it's a list, take the first meaningful value
        for item in yield_value:
            if item:
                if isinstance(item, (int, float)):
                    return str(int(item))
                elif isinstance(item, str):
                    return item
        # If all items are empty, return first as string
        return str(yield_value[0]) if yield_value else None
    
    return str(yield_value)


def _normalize_ingredients(ingredients: Any) -> List[str]:
    """Normalize ingredients list"""
    if not ingredients:
        return []
    
    if isinstance(ingredients, str):
        return [ingredients]
    elif isinstance(ingredients, list):
        result = []
        for ing in ingredients:
            if isinstance(ing, str):
                result.append(ing)
            elif isinstance(ing, dict):
                # Handle structured ingredient
                result.append(ing.get('name') or ing.get('text') or str(ing))
        return result
    
    return []


def _normalize_instructions(instructions: Any) -> str:
    """Normalize instructions (can be string, list of strings, or list of HowToStep objects)"""
    if not instructions:
        return ''
    
    if isinstance(instructions, str):
        # Clean up embedded ingredient lists or extra formatting
        return _clean_instruction_text(instructions)
    
    if isinstance(instructions, list):
        steps = []
        for step in instructions:
            if isinstance(step, str):
                steps.append(_clean_instruction_text(step))
            elif isinstance(step, dict):
                # Handle HowToStep format
                text = step.get('text') or step.get('@value') or step.get('name')
                if text:
                    steps.append(_clean_instruction_text(text))
        
        return ' || '.join(steps)
    
    return _clean_instruction_text(str(instructions))


def _clean_instruction_text(text: str) -> str:
    """Clean instruction text by removing embedded ingredient lists and fixing formatting"""
    if not text:
        return ''
    
    # Remove embedded ingredient lists that appear after periods
    # Pattern: period followed immediately by number/fraction and measurement units
    # Example: "...let cool.2 cups frozen or fresh cranberries, 1/4 cup maple syrup"
    # This matches: .2 cups, .1/4 cup, .1-2 tbsp, etc.
    text = re.sub(r'\.(\d+[\s\-/]*\d*[\s]*(?:cup|cups|tbsp|tsp|oz|pound|pounds|tablespoon|teaspoons?|tablespoons?)[\s\w,–-]*)+', '.', text, flags=re.IGNORECASE)
    
    # Remove trailing ingredient lists (at the end of the text)
    # Pattern: starts with number/fraction and contains measurement units
    text = re.sub(r'[\s\.]+(\d+[\s\-/]*\d*[\s]*(?:cup|cups|tbsp|tsp|oz|pound|pounds|tablespoon|teaspoons?|tablespoons?)[\s\w,–-]*)+$', '', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Clean up multiple periods
    text = re.sub(r'\.+', '.', text)
    
    # Ensure proper sentence endings
    text = text.strip()
    
    return text


def fetch_and_extract_jsonld(url: str) -> List[Dict]:
    """
    Fetch a URL and extract JSON-LD recipe data
    
    Args:
        url: Recipe URL to fetch
        
    Returns:
        List of recipe dictionaries found
    """
    if not JSONLD_AVAILABLE:
        return []
    
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        return extract_jsonld_recipes(response.text, url)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []


# ============================================================================
# Recipe Manager Class
# ============================================================================

class RecipeManager:
    # Standardized units
    VALID_UNITS = [
        # Volume
        't', 'T', 'C', 'ml', 'L', 'floz', 'pint', 'pints', 'quart', 'quarts',
        # Weight
        'oz', 'lb', 'g', 'kg', 'pound', 'pounds',
        # Counting/Pieces
        'slice', 'slices', 'piece', 'pieces', 'clove', 'cloves',
        'can', 'cans', 'whole', 'each', 'bunch', 'bunches', 'head', 'stalk', 'stalks',
        'pkg', 'package', 'container', 'jar', 'box', 'boxes',
        'bag', 'bags', 'egg', 'eggs', 'stick', 'sticks', 'strip', 'strips',
        'dozen', 'envelope', 'envelopes', 'bottle', 'bottles',
        # Small amounts
        'pinch', 'dash',
        # Measurement
        'inch', 'inches'
    ]
    UNIT_DISPLAY = {
        # Volume
        't': 'tsp',
        'T': 'Tbsp', 
        'C': 'cup',
        'ml': 'ml',
        'L': 'L',
        'floz': 'fl oz',
        'pint': 'pint',
        'pints': 'pints',
        'quart': 'quart',
        'quarts': 'quarts',
        # Weight
        'oz': 'oz',
        'lb': 'lb',
        'g': 'g',
        'kg': 'kg',
        'pound': 'lb',
        'pounds': 'lb',
        # Counting/Pieces
        'slice': 'slice',
        'slices': 'slices',
        'piece': 'piece',
        'pieces': 'pieces',
        'clove': 'clove',
        'cloves': 'cloves',
        'can': 'can',
        'cans': 'cans',
        'whole': 'whole',
        'each': 'each',
        'bunch': 'bunch',
        'bunches': 'bunches',
        'head': 'head',
        'stalk': 'stalk',
        'stalks': 'stalks',
        'pkg': 'package',
        'package': 'package',
        'container': 'container',
        'jar': 'jar',
        'box': 'box',
        'boxes': 'boxes',
        'bag': 'bag',
        'bags': 'bags',
        'egg': 'egg',
        'eggs': 'eggs',
        'stick': 'stick',
        'sticks': 'sticks',
        'strip': 'strip',
        'strips': 'strips',
        'dozen': 'dozen',
        'envelope': 'envelope',
        'envelopes': 'envelopes',
        'bottle': 'bottle',
        'bottles': 'bottles',
        # Small amounts
        'pinch': 'pinch',
        'dash': 'dash',
        # Measurement
        'inch': 'inch',
        'inches': 'inches'
    }
    
    # Unit normalization map (variations -> standard)
    UNIT_NORMALIZATION = {
        'lbs': 'lb',
        'pounds': 'lb',
        'pound': 'lb',
        'pints': 'pint',
        'quarts': 'quart',
        'pkgs': 'pkg',
        'pkt': 'pkg',
        'liters': 'L',
        'bags': 'bag',
        'bunches': 'bunch',
        'boxes': 'box',
        'eggs': 'egg',
        'sticks': 'stick',
        'strips': 'strip',
        'envelopes': 'envelope',
        'bottles': 'bottle',
        'inches': 'inch',
        'pcs': 'pieces',
        # Volume units
        'cup': 'C',
        'cups': 'C',
        'tablespoon': 'T',
        'tablespoons': 'T',
        'tbsp': 'T',
        'tbsps': 'T',
        'tbsp.': 'T',
        'teaspoon': 't',
        'teaspoons': 't',
        'tsp': 't',
        'tsps': 't',
        'tsp.': 't',
    }
    
    def __init__(self, csv_file='recipes.csv'):
        self.csv_file = Path(csv_file)
        self.categories = [
            'meal', 'side', 'dessert', 'breakfast', 'snack', 'drink',
            'sauce', 'dressing', 'baked good', 'appetizer', 'condiment', 
            'base/component', 'other',
            # Additional categories from extracted recipes
            'beverage', 'bread', 'main dish', 'side dish'
        ]
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file if it doesn't exist"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'title', 'url', 'category', 'ingredients', 
                    'instructions', 'cook_time', 'servings', 'image_url', 'notes'
                ])
            print(f"Created {self.csv_file}")
    
    def _parse_fraction(self, fraction_str: str) -> float:
        """Convert fraction string to decimal (e.g., '1/2' -> 0.5, '1 1/2' -> 1.5)"""
        fraction_str = fraction_str.strip()
        
        # Handle mixed numbers like "1 1/2"
        if ' ' in fraction_str:
            parts = fraction_str.split()
            whole = float(parts[0])
            frac = self._parse_fraction(parts[1])
            return whole + frac
        
        # Handle fractions like "1/2"
        if '/' in fraction_str:
            numerator, denominator = fraction_str.split('/')
            return float(numerator) / float(denominator)
        
        # Regular number
        return float(fraction_str)
    
    def _normalize_quantity(self, quantity_str: str) -> tuple:
        """
        Parse and normalize a quantity string into (number, unit)
        Examples: "1/2 C" -> (0.5, "C"), "2 T" -> (2.0, "T"), "1.5 t" -> (1.5, "t")
        """
        quantity_str = quantity_str.strip()
        
        # Pattern to match number (with fractions) and unit
        # Matches: "1/2 C", "1 1/2 C", "2.5 t", "3T" (no space)
        pattern = r'^([\d\s./]+)\s*([a-zA-Z]+)?$'
        match = re.match(pattern, quantity_str)
        
        if not match:
            raise ValueError(f"Invalid quantity format: '{quantity_str}'")
        
        number_part = match.group(1).strip()
        unit_part = match.group(2) if match.group(2) else ''
        
        # Parse the number (handles fractions and decimals)
        try:
            number = self._parse_fraction(number_part)
        except:
            raise ValueError(f"Invalid number format: '{number_part}'")
        
        # Normalize unit (handle variations)
        if unit_part:
            unit_lower = unit_part.lower()
            # Check if it needs normalization
            if unit_lower in self.UNIT_NORMALIZATION:
                unit_part = self.UNIT_NORMALIZATION[unit_lower]
            # Preserve case for standard units (C, T, t)
            elif unit_part == 'C' or (unit_lower == 'c' and unit_part.isupper()):
                unit_part = 'C'
            elif unit_part == 'T' or (unit_lower == 't' and len(unit_part) == 1 and unit_part.isupper()):
                unit_part = 'T'
            elif unit_lower == 't':
                unit_part = 't'
            else:
                unit_part = unit_lower
        
        # Validate unit
        if unit_part and unit_part not in self.VALID_UNITS:
            valid_units_str = ', '.join(self.VALID_UNITS)
            raise ValueError(f"Invalid unit '{unit_part}'. Valid units: {valid_units_str}")
        
        return (number, unit_part)
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """Capitalize first letter of each word in ingredient name"""
        return ' '.join(word.capitalize() for word in name.split())
    
    def _format_ingredient(self, quantity_num: float, unit: str, name: str) -> str:
        """Format ingredient for display: '1.5 cup Flour'"""
        # Convert float to nice display (remove .0 for whole numbers)
        if quantity_num == int(quantity_num):
            qty_display = str(int(quantity_num))
        else:
            qty_display = str(quantity_num)
        
        # Get unit display name
        unit_display = self.UNIT_DISPLAY.get(unit, unit) if unit else ''
        
        # Format: "1.5 cup Flour" or "2 Flour" (if no unit)
        if unit_display:
            return f"{qty_display} {unit_display} {name}"
        else:
            return f"{qty_display} {name}"
    
    def _parse_ingredient_input(self, ingredient_str: str) -> Dict:
        """
        Parse a freeform ingredient string into structured format.
        Examples:
          "1/2 C cottage cheese" -> {"quantity": 0.5, "unit": "C", "name": "Cottage Cheese"}
          "2 eggs" -> {"quantity": 2.0, "unit": "", "name": "Eggs"}
          "8 Ounces Cream Cheese" -> {"quantity": 8.0, "unit": "oz", "name": "Cream Cheese"}
        """
        ingredient_str = ingredient_str.strip()
        
        # Try to extract quantity, unit, and name
        # Pattern: (number with fractions) (optional unit) (ingredient name)
        pattern = r'^([\d\s./]+)\s*([a-zA-Z]+)?\s+(.+)$'
        match = re.match(pattern, ingredient_str)
        
        if not match:
            # No quantity found - assume it's just the ingredient name
            return {
                'quantity': 1.0,
                'unit': '',
                'name': self._normalize_ingredient_name(ingredient_str)
            }
        
        number_part = match.group(1).strip()
        unit_part = match.group(2) if match.group(2) else ''
        name_part = match.group(3).strip()
        
        # Normalize unit first (before checking if it's valid)
        if unit_part:
            unit_lower = unit_part.lower()
            if unit_lower in self.UNIT_NORMALIZATION:
                unit_part = self.UNIT_NORMALIZATION[unit_lower]
            # Preserve case for standard units (C, T, t)
            elif unit_lower == 'c' and unit_part.isupper():
                unit_part = 'C'
            elif unit_lower == 't' and len(unit_part) == 1 and unit_part.isupper():
                unit_part = 'T'
            elif unit_lower == 't' and len(unit_part) == 1:
                unit_part = 't'
        
        # Check if the "unit" is actually part of the name (not a valid unit)
        if unit_part and unit_part not in self.VALID_UNITS:
            # It's not a unit, it's part of the name
            # But check if the name itself contains a unit we can extract
            name_with_unit = f"{unit_part} {name_part}"
            
            # Try to extract unit from the name (e.g., "Ounces Cream Cheese" -> "oz" + "Cream Cheese")
            name_unit_match = re.match(r'^(ounces?|oz|pounds?|lbs?|cups?|tablespoons?|teaspoons?|tbsp|tsp)\s+(.+)$', name_with_unit, re.IGNORECASE)
            if name_unit_match:
                potential_unit = name_unit_match.group(1).lower()
                clean_name = name_unit_match.group(2).strip()
                
                # Normalize the extracted unit
                if potential_unit in self.UNIT_NORMALIZATION:
                    unit_part = self.UNIT_NORMALIZATION[potential_unit]
                elif potential_unit in ['ounces', 'ounce']:
                    unit_part = 'oz'
                elif potential_unit in ['pounds', 'pound']:
                    unit_part = 'lb'
                elif potential_unit in ['cups', 'cup']:
                    unit_part = 'C'
                elif potential_unit in ['tablespoons', 'tablespoon', 'tbsp']:
                    unit_part = 'T'
                elif potential_unit in ['teaspoons', 'teaspoon', 'tsp']:
                    unit_part = 't'
                
                if unit_part in self.VALID_UNITS:
                    name_part = clean_name
                else:
                    # Still not a valid unit, keep as name
                    name_part = name_with_unit
                    unit_part = ''
            else:
                name_part = name_with_unit
                unit_part = ''
        
        # Parse quantity
        try:
            quantity = self._parse_fraction(number_part)
        except:
            raise ValueError(f"Invalid number format: '{number_part}'")
        
        return {
            'quantity': quantity,
            'unit': unit_part,
            'name': self._normalize_ingredient_name(name_part)
        }
    
    def _prompt_for_ingredient(self) -> Optional[Dict]:
        """Prompt user for a single ingredient with validation"""
        print("\nEnter ingredient (or press Enter to finish):")
        print("Examples: '1/2 C cottage cheese', '2 T butter', '3 eggs'")
        print(f"Valid units: {', '.join(self.VALID_UNITS)}")
        
        ingredient_str = input("Ingredient: ").strip()
        
        if not ingredient_str:
            return None
        
        try:
            return self._parse_ingredient_input(ingredient_str)
        except ValueError as e:
            print(f"ERROR: {e}")
            print("Please try again.")
            return self._prompt_for_ingredient()
    
    def scrape_recipe(self, url: str) -> Optional[Dict]:
        """
        Scrape recipe from URL using recipe-scrapers library.
        Falls back to JSON-LD extraction if recipe-scrapers fails.
        """
        # Try recipe-scrapers first
        try:
            print(f"Scraping recipe from: {url}")
            scraper = scrape_me(url)
            
            # Parse scraped ingredients into structured format
            raw_ingredients = scraper.ingredients()
            parsed_ingredients = []
            
            print(f"\nParsing {len(raw_ingredients)} ingredients...")
            for raw_ing in raw_ingredients:
                try:
                    parsed = self._parse_ingredient_input(raw_ing)
                    parsed_ingredients.append(parsed)
                except ValueError as e:
                    # If parsing fails, ask user to manually enter it
                    print(f"\nCouldn't automatically parse: '{raw_ing}'")
                    print(f"Error: {e}")
                    print("Please enter manually:")
                    manual_parsed = self._prompt_for_ingredient()
                    if manual_parsed:
                        parsed_ingredients.append(manual_parsed)
            
            recipe = {
                'title': scraper.title(),
                'url': url,
                'ingredients': parsed_ingredients,
                'instructions': scraper.instructions(),
                'cook_time': scraper.total_time() if scraper.total_time() else 'N/A',
                'servings': scraper.yields() if scraper.yields() else 'N/A',
                'image_url': scraper.image() if scraper.image() else '',
            }
            
            print(f"Found recipe: {recipe['title']}")
            return recipe
            
        except Exception as e:
            print(f"ERROR with recipe-scrapers: {e}")
            print("Trying JSON-LD structured data extraction as fallback...")
            
            # Fallback to JSON-LD extraction
            if JSONLD_AVAILABLE:
                try:
                    recipes = fetch_and_extract_jsonld(url)
                    if recipes and len(recipes) > 0:
                        jsonld_recipe = recipes[0]  # Use first recipe found
                        print(f"Found recipe via JSON-LD: {jsonld_recipe.get('title', 'Unknown')}")
                        
                        # Convert JSON-LD format to our format
                        parsed_ingredients = []
                        for ing in jsonld_recipe.get('ingredients', []):
                            try:
                                parsed = self._parse_ingredient_input(ing)
                                parsed_ingredients.append(parsed)
                            except ValueError:
                                # If parsing fails, use as-is
                                parsed_ingredients.append({'quantity': 1.0, 'unit': '', 'name': ing})
                        
                        recipe = {
                            'title': jsonld_recipe.get('title', 'Unknown Recipe'),
                            'url': url,
                            'ingredients': parsed_ingredients,
                            'instructions': jsonld_recipe.get('instructions', ''),
                            'cook_time': jsonld_recipe.get('cook_time', 'N/A'),
                            'servings': jsonld_recipe.get('servings', 'N/A'),
                            'image_url': jsonld_recipe.get('image_url', ''),
                        }
                        
                        print(f"Successfully extracted recipe: {recipe['title']}")
                        return recipe
                    else:
                        print("No JSON-LD recipe data found on this page.")
                except Exception as jsonld_error:
                    print(f"ERROR with JSON-LD extraction: {jsonld_error}")
            
            print("The site may not be supported or the URL may be incorrect.")
            return None
    
    def add_recipe(self, url: str, category: Optional[str] = None, notes: str = ''):
        """Scrape and add a recipe to the database"""
        recipe = self.scrape_recipe(url)
        
        if not recipe:
            return False
        
        # Ask for category if not provided
        if not category:
            print(f"\nCategorize '{recipe['title']}'")
            print("Available categories:", ', '.join(self.categories))
            category = input("Enter category (or press Enter for 'meal'): ").strip().lower()
            
            if not category:
                category = 'meal'
            
            # Add custom category if not in list
            if category not in self.categories:
                print(f"Adding new category: {category}")
                self.categories.append(category)
        
        # Add category and notes to recipe
        recipe['category'] = category
        recipe['notes'] = notes
        
        # Convert lists to JSON strings for CSV storage
        recipe['ingredients'] = json.dumps(recipe['ingredients'])
        recipe['instructions'] = recipe['instructions'].replace('\n', ' || ')
        
        # Append to CSV
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'title', 'url', 'category', 'ingredients', 
                'instructions', 'cook_time', 'servings', 'image_url', 'notes'
            ])
            writer.writerow(recipe)
        
        print(f"SUCCESS: Added '{recipe['title']}' to your recipe collection!")
        return True
    
    def add_manual_recipe(self):
        """Manually add a recipe by entering all details"""
        print("\n" + "=" * 80)
        print("MANUALLY ADD RECIPE")
        print("=" * 80)
        
        # Get recipe details
        title = input("\nRecipe Title: ").strip()
        if not title:
            print("ERROR: Title is required.")
            return False
        
        # Category
        print(f"\nAvailable categories: {', '.join(self.categories)}")
        category = input("Category (or press Enter for 'meal'): ").strip().lower()
        if not category:
            category = 'meal'
        if category not in self.categories:
            self.categories.append(category)
        
        # Source/URL (optional)
        url = input("\nSource/URL (optional, press Enter to skip): ").strip()
        if not url:
            url = f"manual-{len(pd.read_csv(self.csv_file)) + 1}"  # Generate ID
        
        # Servings
        servings = input("Servings (e.g., '4 servings' or '8 cookies'): ").strip()
        if not servings:
            servings = 'N/A'
        
        # Cook time
        cook_time = input("Total cook time (e.g., '30 mins' or '1 hour'): ").strip()
        if not cook_time:
            cook_time = 'N/A'
        
        # Ingredients
        print("\nIngredients:")
        print("Enter ingredients one per line. Press Enter on empty line when done.")
        print("Examples: '1/2 C cottage cheese', '2 T butter', '3 eggs'")
        print(f"Valid units: {', '.join(self.VALID_UNITS)}")
        ingredients = []
        counter = 1
        while True:
            print(f"\nIngredient {counter}:")
            parsed_ingredient = self._prompt_for_ingredient()
            if not parsed_ingredient:
                break
            ingredients.append(parsed_ingredient)
            # Show what was parsed
            formatted = self._format_ingredient(
                parsed_ingredient['quantity'], 
                parsed_ingredient['unit'], 
                parsed_ingredient['name']
            )
            print(f"  -> Added: {formatted}")
            counter += 1
        
        if not ingredients:
            print("ERROR: At least one ingredient is required.")
            return False
        
        # Instructions
        print("\nInstructions:")
        print("Enter instructions. You can use multiple lines.")
        print("Type 'DONE' on a new line when finished.")
        instructions_lines = []
        while True:
            line = input()
            if line.strip().upper() == 'DONE':
                break
            instructions_lines.append(line)
        
        instructions = ' || '.join(instructions_lines) if instructions_lines else 'See original recipe'
        
        # Notes
        notes = input("\nNotes (optional): ").strip()
        
        # Image URL (optional)
        image_url = input("Image URL (optional): ").strip()
        
        # Create recipe dict
        recipe = {
            'title': title,
            'url': url,
            'category': category,
            'ingredients': json.dumps(ingredients),
            'instructions': instructions,
            'cook_time': cook_time,
            'servings': servings,
            'image_url': image_url,
            'notes': notes
        }
        
        # Save to CSV
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'title', 'url', 'category', 'ingredients', 
                'instructions', 'cook_time', 'servings', 'image_url', 'notes'
            ])
            writer.writerow(recipe)
        
        print(f"\nSUCCESS: Added '{title}' to your recipe collection!")
        print(f"   Category: {category} | Servings: {servings} | Time: {cook_time}")
        return True
    
    def _parse_recipe_from_text(self, text_block: str) -> Optional[Dict]:
        """Parse a single recipe from a text block"""
        lines = text_block.strip().split('\n')
        recipe_data = {
            'title': '',
            'category': 'meal',
            'servings': 'N/A',
            'cook_time': 'N/A',
            'url': '',
            'ingredients': [],
            'instructions': '',
            'notes': '',
            'image_url': ''
        }
        
        current_section = None
        instructions_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines unless in instructions
            if not line_stripped and current_section != 'instructions':
                continue
            
            # Skip markdown headers (## Recipe Name)
            if line_stripped.startswith('## '):
                # Extract title from markdown header if Title: not found yet
                if not recipe_data['title']:
                    recipe_data['title'] = line_stripped[3:].strip()
                continue
            
            # Check for field headers
            if line_stripped.lower().startswith('title:'):
                recipe_data['title'] = line_stripped[6:].strip()
            elif line_stripped.lower().startswith('category:'):
                category = line_stripped[9:].strip().lower()
                # Keep category as-is (all categories including new ones are in the list)
                recipe_data['category'] = category
            elif line_stripped.lower().startswith('servings:'):
                recipe_data['servings'] = line_stripped[9:].strip()
            elif line_stripped.lower().startswith('cook time:'):
                recipe_data['cook_time'] = line_stripped[10:].strip()
            elif line_stripped.lower().startswith('source:'):
                recipe_data['url'] = line_stripped[7:].strip()
            elif line_stripped.lower().startswith('notes:'):
                recipe_data['notes'] = line_stripped[6:].strip()
                current_section = 'notes'
            elif line_stripped.lower() == 'ingredients:':
                current_section = 'ingredients'
            elif line_stripped.lower() == 'instructions:':
                current_section = 'instructions'
            elif current_section == 'ingredients':
                # Parse ingredient
                try:
                    parsed_ing = self._parse_ingredient_input(line_stripped)
                    recipe_data['ingredients'].append(parsed_ing)
                except Exception as e:
                    print(f"Warning: Could not parse ingredient '{line_stripped}': {e}")
            elif current_section == 'instructions':
                instructions_lines.append(line_stripped)
            elif current_section == 'notes':
                # Continue accumulating notes
                recipe_data['notes'] += ' ' + line_stripped
        
        # Join instructions
        recipe_data['instructions'] = ' || '.join(instructions_lines) if instructions_lines else 'See source'
        
        # Validate
        if not recipe_data['title']:
            return None
        if not recipe_data['ingredients']:
            print(f"Warning: Recipe '{recipe_data['title']}' has no ingredients")
            return None
        
        # Generate URL if not provided
        if not recipe_data['url']:
            recipe_data['url'] = f"text-import-{len(pd.read_csv(self.csv_file)) + 1}"
        
        return recipe_data
    
    def import_from_txt(self, txt_file: str):
        """Import multiple recipes from a text file (supports .txt and .md formats)"""
        txt_path = Path(txt_file)
        
        if not txt_path.exists():
            print(f"ERROR: File '{txt_file}' not found.")
            return False
        
        print(f"\nImporting recipes from: {txt_file}")
        print("=" * 80)
        
        # Read file
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine separator based on file extension
        if txt_path.suffix.lower() == '.md':
            # Markdown format uses --- as separator
            # Also skip markdown headers (## Recipe Name) and metadata at top
            lines = content.split('\n')
            # Skip header lines until we find the first recipe
            recipe_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('## ') or line.strip().startswith('Title:'):
                    recipe_start = i
                    break
            
            # Split by --- separator
            recipe_blocks = content.split('---')
            # Filter out empty blocks and header metadata
            recipe_blocks = [block.strip() for block in recipe_blocks if block.strip() and 'Title:' in block]
        else:
            # Text format uses ***** as separator
            recipe_blocks = content.split('*****')
        
        imported_count = 0
        failed_count = 0
        
        for idx, block in enumerate(recipe_blocks, 1):
            block = block.strip()
            if not block:
                continue
            
            print(f"\nProcessing recipe {idx}...")
            recipe = self._parse_recipe_from_text(block)
            
            if recipe:
                # Save to CSV
                try:
                    with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=[
                            'title', 'url', 'category', 'ingredients', 
                            'instructions', 'cook_time', 'servings', 'image_url', 'notes'
                        ])
                        # Convert ingredients list to JSON
                        recipe_to_save = recipe.copy()
                        recipe_to_save['ingredients'] = json.dumps(recipe['ingredients'])
                        writer.writerow(recipe_to_save)
                    
                    print(f"  SUCCESS: Added '{recipe['title']}'")
                    print(f"    Category: {recipe['category']} | Ingredients: {len(recipe['ingredients'])}")
                    imported_count += 1
                except Exception as e:
                    print(f"  ERROR: Failed to save '{recipe.get('title', 'Unknown')}': {e}")
                    failed_count += 1
            else:
                print(f"  ERROR: Could not parse recipe block {idx}")
                failed_count += 1
        
        print("\n" + "=" * 80)
        print(f"Import complete: {imported_count} successful, {failed_count} failed")
        print("=" * 80)
        return True
    
    def update_recipe(self, title_search: Optional[str] = None):
        """Update an existing recipe"""
        df = pd.read_csv(self.csv_file)
        
        if df.empty:
            print("No recipes found.")
            return False
        
        # Find recipe
        if title_search:
            matches = df[df['title'].str.contains(title_search, case=False, na=False)]
            if matches.empty:
                print(f"No recipe found matching '{title_search}'")
                return False
            elif len(matches) > 1:
                print(f"\nFound {len(matches)} matching recipes:")
                for idx, row in matches.iterrows():
                    print(f"  {idx + 1}. {row['title']} ({row['category']})")
                choice = input("\nEnter recipe number to update: ").strip()
                try:
                    recipe_idx = int(choice) - 1
                    recipe = matches.iloc[recipe_idx]
                except:
                    print("Invalid selection")
                    return False
            else:
                recipe = matches.iloc[0]
        else:
            # Show all recipes and let user choose
            print("\nAll Recipes:")
            for idx, row in df.iterrows():
                print(f"  {idx + 1}. {row['title']} ({row['category']})")
            choice = input("\nEnter recipe number to update: ").strip()
            try:
                recipe_idx = int(choice) - 1
                recipe = df.iloc[recipe_idx]
            except:
                print("Invalid selection")
                return False
        
        print("\n" + "=" * 80)
        print(f"UPDATING: {recipe['title']}")
        print("=" * 80)
        print("Press Enter to keep current value, or type new value\n")
        
        # Update fields
        new_title = input(f"Title [{recipe['title']}]: ").strip()
        if not new_title:
            new_title = recipe['title']
        
        new_category = input(f"Category [{recipe['category']}]: ").strip().lower()
        if not new_category:
            new_category = recipe['category']
        
        new_servings = input(f"Servings [{recipe['servings']}]: ").strip()
        if not new_servings:
            new_servings = recipe['servings']
        
        new_cook_time = input(f"Cook Time [{recipe['cook_time']}]: ").strip()
        if not new_cook_time:
            new_cook_time = recipe['cook_time']
        
        new_url = input(f"Source/URL [{recipe['url']}]: ").strip()
        if not new_url:
            new_url = recipe['url']
        
        # Ingredients
        print(f"\nCurrent Ingredients:")
        try:
            current_ingredients = json.loads(recipe['ingredients'])
            if isinstance(current_ingredients, list) and current_ingredients:
                if isinstance(current_ingredients[0], dict):
                    # New format
                    for i, ing in enumerate(current_ingredients, 1):
                        formatted = self._format_ingredient(ing['quantity'], ing['unit'], ing['name'])
                        print(f"  {i}. {formatted}")
                else:
                    # Old format
                    for i, ing in enumerate(current_ingredients, 1):
                        print(f"  {i}. {ing}")
        except:
            print("  (Could not parse ingredients)")
        
        update_ingredients = input("\nUpdate ingredients? (y/n): ").strip().lower()
        if update_ingredients == 'y':
            print("\nEnter new ingredients (press Enter on empty line to finish):")
            new_ingredients = []
            counter = 1
            while True:
                print(f"\nIngredient {counter}:")
                parsed_ingredient = self._prompt_for_ingredient()
                if not parsed_ingredient:
                    break
                new_ingredients.append(parsed_ingredient)
                formatted = self._format_ingredient(
                    parsed_ingredient['quantity'], 
                    parsed_ingredient['unit'], 
                    parsed_ingredient['name']
                )
                print(f"  -> Added: {formatted}")
                counter += 1
        else:
            new_ingredients = current_ingredients
        
        # Instructions
        print(f"\nCurrent Instructions: {recipe['instructions'][:100]}...")
        update_instructions = input("\nUpdate instructions? (y/n): ").strip().lower()
        if update_instructions == 'y':
            print("\nEnter new instructions (type 'DONE' on new line when finished):")
            instructions_lines = []
            while True:
                line = input()
                if line.strip().upper() == 'DONE':
                    break
                instructions_lines.append(line)
            new_instructions = ' || '.join(instructions_lines) if instructions_lines else recipe['instructions']
        else:
            new_instructions = recipe['instructions']
        
        # Notes
        new_notes = input(f"\nNotes [{recipe['notes']}]: ").strip()
        if not new_notes:
            new_notes = recipe['notes']
        
        # Update in dataframe
        df.at[recipe.name, 'title'] = new_title
        df.at[recipe.name, 'category'] = new_category
        df.at[recipe.name, 'servings'] = new_servings
        df.at[recipe.name, 'cook_time'] = new_cook_time
        df.at[recipe.name, 'url'] = new_url
        df.at[recipe.name, 'ingredients'] = json.dumps(new_ingredients)
        df.at[recipe.name, 'instructions'] = new_instructions
        df.at[recipe.name, 'notes'] = new_notes
        
        # Save back to CSV
        df.to_csv(self.csv_file, index=False)
        
        print("\n" + "=" * 80)
        print(f"SUCCESS: Updated '{new_title}'!")
        print("=" * 80)
        return True
    
    def list_recipes(self, category: Optional[str] = None):
        """List all recipes, optionally filtered by category"""
        df = pd.read_csv(self.csv_file)
        
        if df.empty:
            print("No recipes found. Add some with: python recipe_manager.py add <url>")
            return
        
        if category:
            df = df[df['category'].str.lower() == category.lower()]
            print(f"\n{category.upper()} Recipes:")
        else:
            print(f"\nAll Recipes ({len(df)} total):")
        
        print("=" * 80)
        
        for idx, row in df.iterrows():
            print(f"{idx + 1}. {row['title']}")
            print(f"   Category: {row['category']} | Cook Time: {row['cook_time']} | Servings: {row['servings']}")
            print(f"   URL: {row['url']}")
            if row['notes'] and pd.notna(row['notes']):
                print(f"   Notes: {row['notes']}")
            print()
    
    def generate_meal_plan(self, num_meals: int = 3, category: str = 'meal') -> List[Dict]:
        """Randomly select recipes for a meal plan"""
        df = pd.read_csv(self.csv_file)
        
        # Filter by category
        meals_df = df[df['category'].str.lower() == category.lower()]
        
        if len(meals_df) < num_meals:
            print(f"WARNING: Only {len(meals_df)} {category}s available. Need at least {num_meals}.")
            print(f"Add more with: python recipe_manager.py add <url>")
            return []
        
        # Randomly select meals
        selected = meals_df.sample(n=num_meals)
        
        print(f"\nYOUR {num_meals}-MEAL WEEKLY PLAN")
        print("=" * 80)
        
        meal_plan = []
        for idx, (_, row) in enumerate(selected.iterrows(), 1):
            print(f"\nMeal {idx}: {row['title']}")
            print(f"  Cook Time: {row['cook_time']} | Servings: {row['servings']}")
            print(f"  URL: {row['url']}")
            
            # Parse ingredients back from JSON
            ingredients = json.loads(row['ingredients'])
            
            meal_plan.append({
                'title': row['title'],
                'url': row['url'],
                'ingredients': ingredients,
                'cook_time': row['cook_time'],
                'servings': row['servings']
            })
        
        return meal_plan
    
    def generate_shopping_list(self, meal_plan: List[Dict]):
        """Generate consolidated shopping list from meal plan"""
        if not meal_plan:
            print("No meal plan provided.")
            return
        
        print("\n" + "=" * 80)
        print("CONSOLIDATED SHOPPING LIST")
        print("=" * 80)
        
        # Consolidate ingredients by name and unit
        # ingredient_map: {(name, unit): total_quantity}
        ingredient_map = defaultdict(float)
        
        for meal in meal_plan:
            ingredients = meal['ingredients']
            # Handle both old format (strings) and new format (dicts)
            if isinstance(ingredients, str):
                # Old format - just display as-is
                ingredients = json.loads(ingredients)
                for ing in ingredients:
                    if isinstance(ing, str):
                        # Old string format - can't consolidate
                        ingredient_map[(ing, 'raw')] = 1
                    else:
                        # New dict format
                        key = (ing['name'], ing['unit'])
                        ingredient_map[key] += ing['quantity']
            else:
                # New format - list of dicts
                for ing in ingredients:
                    key = (ing['name'], ing['unit'])
                    ingredient_map[key] += ing['quantity']
        
        # Sort ingredients by name
        sorted_ingredients = sorted(ingredient_map.items(), key=lambda x: x[0][0])
        
        # Print consolidated list
        print("\nIngredients Needed:\n")
        for idx, ((name, unit), quantity) in enumerate(sorted_ingredients, 1):
            if unit == 'raw':
                # Old format - just print the name (which is the full string)
                print(f"{idx}. {name}")
            else:
                # New format - format nicely
                formatted = self._format_ingredient(quantity, unit, name)
                print(f"{idx}. {formatted}")
        
        print("\n" + "=" * 80)
        print(f"Total unique ingredients: {len(sorted_ingredients)}")
        print("=" * 80)
    
    def search_recipes(self, query: str):
        """Search recipes by title or ingredient"""
        df = pd.read_csv(self.csv_file)
        
        if df.empty:
            print("No recipes found.")
            return
        
        query = query.lower()
        
        # Search in title
        title_matches = df[df['title'].str.lower().str.contains(query, na=False)]
        
        # Search in ingredients
        ingredient_matches = df[df['ingredients'].str.lower().str.contains(query, na=False)]
        
        # Combine and remove duplicates
        results = pd.concat([title_matches, ingredient_matches]).drop_duplicates()
        
        if results.empty:
            print(f"No recipes found matching '{query}'")
            return
        
        print(f"\nSearch results for '{query}':")
        print("=" * 80)
        
        for idx, row in results.iterrows():
            print(f"\n{row['title']}")
            print(f"  Category: {row['category']} | URL: {row['url']}")


def main():
    manager = RecipeManager()
    
    if len(sys.argv) < 2:
        print("=" * 80)
        print("RECIPE MANAGER")
        print("=" * 80)
        print("\nUsage:")
        print("  python recipe_manager_standalone.py add <url> [category] [notes]")
        print("  python recipe_manager_standalone.py manual")
        print("  python recipe_manager_standalone.py import-txt <file.txt>")
        print("  python recipe_manager_standalone.py update [recipe_title]")
        print("  python recipe_manager_standalone.py list [category]")
        print("  python recipe_manager_standalone.py plan [num_meals]")
        print("  python recipe_manager_standalone.py search <query>")
        print("\nExamples:")
        print("  python recipe_manager_standalone.py add https://www.allrecipes.com/recipe/12345/")
        print("  python recipe_manager_standalone.py add <url> dessert 'Family favorite'")
        print("  python recipe_manager_standalone.py manual")
        print("  python recipe_manager_standalone.py import-txt my_recipes.txt")
        print("  python recipe_manager_standalone.py update 'Cottage Cheese Flatbread'")
        print("  python recipe_manager_standalone.py update")
        print("  python recipe_manager_standalone.py list")
        print("  python recipe_manager_standalone.py list meal")
        print("  python recipe_manager_standalone.py plan 5")
        print("  python recipe_manager_standalone.py search chicken")
        print("\nCategories: meal, side, dessert, breakfast, snack, drink, sauce, dressing,")
        print("            baked good, appetizer, condiment, base/component, other")
        print("=" * 80)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Usage: python recipe_manager_standalone.py add <url> [category] [notes]")
            return
        
        url = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else None
        notes = ' '.join(sys.argv[4:]) if len(sys.argv) > 4 else ''
        
        manager.add_recipe(url, category, notes)
    
    elif command == 'manual':
        manager.add_manual_recipe()
    
    elif command == 'import-txt':
        if len(sys.argv) < 3:
            print("Usage: python recipe_manager_standalone.py import-txt <file.txt>")
            return
        
        txt_file = sys.argv[2]
        manager.import_from_txt(txt_file)
    
    elif command == 'update':
        title_search = sys.argv[2] if len(sys.argv) > 2 else None
        manager.update_recipe(title_search)
    
    elif command == 'list':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        manager.list_recipes(category)
    
    elif command == 'plan':
        num_meals = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        meal_plan = manager.generate_meal_plan(num_meals)
        
        if meal_plan:
            print("\nGenerating shopping list...")
            manager.generate_shopping_list(meal_plan)
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("Usage: python recipe_manager_standalone.py search <query>")
            return
        
        query = ' '.join(sys.argv[2:])
        manager.search_recipes(query)
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, manual, import-txt, update, list, plan, search")


if __name__ == "__main__":
    main()
