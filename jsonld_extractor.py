#!/usr/bin/env python3
"""
JSON-LD Recipe Extractor

Extracts recipe data from JSON-LD structured data (schema.org Recipe format).
This is often more reliable than HTML scraping since many recipe sites use
structured data for SEO.

Based on the approach used by obsidian-recipe-grabber:
https://github.com/seethroughdev/obsidian-recipe-grabber
"""

import json
import re
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup
import requests


def extract_jsonld_recipes(html: str, url: str = '') -> List[Dict]:
    """
    Extract recipe data from JSON-LD structured data in HTML
    
    Args:
        html: HTML content of the page
        url: Source URL (optional)
        
    Returns:
        List of recipe dictionaries found in the page
    """
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
    
    import re
    
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
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        return extract_jsonld_recipes(response.text, url)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python jsonld_extractor.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"Fetching and extracting JSON-LD recipes from: {url}")
    
    recipes = fetch_and_extract_jsonld(url)
    
    if recipes:
        print(f"\nFound {len(recipes)} recipe(s):\n")
        for i, recipe in enumerate(recipes, 1):
            print(f"Recipe {i}:")
            print(f"  Title: {recipe.get('title', 'N/A')}")
            print(f"  Cook Time: {recipe.get('cook_time', 'N/A')}")
            print(f"  Servings: {recipe.get('servings', 'N/A')}")
            print(f"  Ingredients: {len(recipe.get('ingredients', []))} items")
            print(f"  Instructions: {len(recipe.get('instructions', '').split('||'))} steps")
            print()
    else:
        print("No JSON-LD recipe data found on this page.")
