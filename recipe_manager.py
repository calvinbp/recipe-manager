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
        print("  python recipe_manager.py add <url> [category] [notes]")
        print("  python recipe_manager.py manual")
        print("  python recipe_manager.py import-txt <file.txt>")
        print("  python recipe_manager.py update [recipe_title]")
        print("  python recipe_manager.py list [category]")
        print("  python recipe_manager.py plan [num_meals]")
        print("  python recipe_manager.py search <query>")
        print("\nExamples:")
        print("  python recipe_manager.py add https://www.allrecipes.com/recipe/12345/")
        print("  python recipe_manager.py add <url> dessert 'Family favorite'")
        print("  python recipe_manager.py manual")
        print("  python recipe_manager.py import-txt my_recipes.txt")
        print("  python recipe_manager.py update 'Cottage Cheese Flatbread'")
        print("  python recipe_manager.py update")
        print("  python recipe_manager.py list")
        print("  python recipe_manager.py list meal")
        print("  python recipe_manager.py plan 5")
        print("  python recipe_manager.py search chicken")
        print("\nCategories: meal, side, dessert, breakfast, snack, drink, sauce, dressing,")
        print("            baked good, appetizer, condiment, base/component, other")
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
    
    elif command == 'import-txt':
        if len(sys.argv) < 3:
            print("Usage: python recipe_manager.py import-txt <file.txt>")
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
            print("Usage: python recipe_manager.py search <query>")
            return
        
        query = ' '.join(sys.argv[2:])
        manager.search_recipes(query)
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, manual, import-txt, update, list, plan, search")


if __name__ == "__main__":
    main()
