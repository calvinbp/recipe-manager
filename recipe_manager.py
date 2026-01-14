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
    from recipe_scrapers import scrape_me_now
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
    def __init__(self, csv_file='recipes.csv'):
        self.csv_file = Path(csv_file)
        self.categories = ['meal', 'side', 'dessert', 'breakfast', 'snack', 'drink']
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
    
    def scrape_recipe(self, url: str) -> Optional[Dict]:
        """Scrape recipe from URL using recipe-scrapers"""
        try:
            print(f"Scraping recipe from: {url}")
            scraper = scrape_me_now(url)
            
            recipe = {
                'title': scraper.title(),
                'url': url,
                'ingredients': scraper.ingredients(),
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
        ingredients = []
        counter = 1
        while True:
            ingredient = input(f"  {counter}. ").strip()
            if not ingredient:
                break
            ingredients.append(ingredient)
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
        
        # Group all ingredients
        all_ingredients = []
        for meal in meal_plan:
            all_ingredients.extend(meal['ingredients'])
        
        # Try to combine similar ingredients (basic grouping)
        ingredient_groups = defaultdict(list)
        
        for ingredient in all_ingredients:
            # Extract base ingredient (rough heuristic)
            # This is simplified - you could make it more sophisticated
            base = ingredient.lower()
            
            # Remove common measurements to group similar items
            for word in ['cup', 'cups', 'tablespoon', 'tablespoons', 'tbsp', 
                        'teaspoon', 'teaspoons', 'tsp', 'pound', 'pounds', 
                        'lb', 'lbs', 'ounce', 'ounces', 'oz', 'gram', 'grams', 'g']:
                base = base.replace(word, '').strip()
            
            # Use first few words as key
            key = ' '.join(base.split()[:3]) if base else ingredient
            ingredient_groups[key].append(ingredient)
        
        # Print organized by similarity
        print("\nIngredients Needed:\n")
        for idx, (key, ingredients) in enumerate(ingredient_groups.items(), 1):
            if len(ingredients) == 1:
                print(f"{idx}. {ingredients[0]}")
            else:
                print(f"{idx}. {key}:")
                for ing in ingredients:
                    print(f"     - {ing}")
        
        print("\n" + "=" * 80)
        print(f"Total ingredient items: {len(all_ingredients)}")
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
