#!/usr/bin/env python3
"""
Recipe Manager
- Add recipes from URLs
- Add recipes manually
- Categorize recipes (meal, side, dessert, etc.)
- Generate weekly meal plans
- Create consolidated shopping lists
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List, Dict, Optional
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


class RecipeManager:
    # Standardized units
    VALID_UNITS = [
        # Volume
        't', 'T', 'C', 'ml', 'L', 'floz',
        # Weight
        'oz', 'lb', 'g', 'kg',
        # Counting/Pieces
        'slice', 'slices', 'piece', 'pieces', 'clove', 'cloves',
        'can', 'cans', 'whole', 'each', 'bunch', 'head', 'stalk', 'stalks',
        'pkg', 'package', 'container', 'jar', 'box'
    ]
    UNIT_DISPLAY = {
        # Volume
        't': 'tsp',
        'T': 'Tbsp', 
        'C': 'cup',
        'ml': 'ml',
        'L': 'L',
        'floz': 'fl oz',
        # Weight
        'oz': 'oz',
        'lb': 'lb',
        'g': 'g',
        'kg': 'kg',
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
        'head': 'head',
        'stalk': 'stalk',
        'stalks': 'stalks',
        'pkg': 'package',
        'package': 'package',
        'container': 'container',
        'jar': 'jar',
        'box': 'box'
    }
    
    def __init__(self, csv_file='recipes.csv'):
        self.csv_file = Path(csv_file)
        self.categories = [
            'meal', 'side', 'dessert', 'breakfast', 'snack', 'drink',
            'sauce', 'dressing', 'baked good', 'appetizer', 'condiment', 
            'base/component', 'other'
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
        
        # Check if the "unit" is actually part of the name (not a valid unit)
        if unit_part and unit_part not in self.VALID_UNITS:
            # It's not a unit, it's part of the name
            name_part = f"{unit_part} {name_part}"
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
        """Scrape recipe from URL using recipe-scrapers"""
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
            print(f"ERROR scraping recipe: {e}")
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
        print("  python recipe_manager.py add <url> [category] [notes]")
        print("  python recipe_manager.py manual")
        print("  python recipe_manager.py list [category]")
        print("  python recipe_manager.py plan [num_meals]")
        print("  python recipe_manager.py search <query>")
        print("\nExamples:")
        print("  python recipe_manager.py add https://www.allrecipes.com/recipe/12345/")
        print("  python recipe_manager.py add <url> dessert 'Family favorite'")
        print("  python recipe_manager.py manual")
        print("  python recipe_manager.py list")
        print("  python recipe_manager.py list meal")
        print("  python recipe_manager.py plan 5")
        print("  python recipe_manager.py search chicken")
        print("\nCategories: meal, side, dessert, breakfast, snack, drink (or create your own)")
        print("=" * 80)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Usage: python recipe_manager.py add <url> [category] [notes]")
            return
        
        url = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else None
        notes = ' '.join(sys.argv[4:]) if len(sys.argv) > 4 else ''
        
        manager.add_recipe(url, category, notes)
    
    elif command == 'manual':
        manager.add_manual_recipe()
    
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
            print("Usage: python recipe_manager.py search <query>")
            return
        
        query = ' '.join(sys.argv[2:])
        manager.search_recipes(query)
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, manual, list, plan, search")


if __name__ == "__main__":
    main()
