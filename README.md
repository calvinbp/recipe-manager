# 🍳 Recipe Manager

A Python command-line tool to collect, organize, and manage your recipes. Automatically scrape recipes from websites, manually add family recipes, generate random meal plans, and create consolidated shopping lists.

## ✨ Features

- 🌐 **Auto-scrape recipes** from 100+ popular recipe websites (AllRecipes, NYT Cooking, Food Network, etc.)
- ✍️ **Manually add recipes** from cookbooks, family recipes, or handwritten notes
- 📊 **Categorize recipes** (meal, side, dessert, breakfast, snack, drink, or custom categories)
- 🎲 **Random meal planning** - Generate weekly meal plans with X number of meals
- 🛒 **Shopping list generation** - Automatically consolidate ingredients from multiple recipes
- 🔍 **Search functionality** - Find recipes by title or ingredient
- 💾 **Simple CSV storage** - Easy to backup and edit manually if needed
- 📝 **Add personal notes** to any recipe

## 📋 Requirements

- Python 3.7 or higher
- pip (Python package manager)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/calvinbp/recipe-manager.git
cd recipe-manager
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install recipe-scrapers pandas requests beautifulsoup4
```

### 3. You're ready!

The CSV database will be created automatically when you add your first recipe.

## 📖 Usage

### Add Recipe from URL

Automatically scrape recipe details from a URL:

```bash
python recipe_manager.py add "https://www.allrecipes.com/recipe/16354/easy-meatloaf/"
```

Add with category and notes:

```bash
python recipe_manager.py add "https://cooking.nytimes.com/recipes/1015987-chocolate-chip-cookies" dessert "Holiday favorite"
```

### Add Recipe Manually

For recipes from cookbooks, family recipes, or handwritten notes:

```bash
python recipe_manager.py manual
```

This will interactively prompt you for:
- Recipe title
- Category
- Source/URL (optional)
- Servings
- Cook time
- Ingredients (one per line)
- Instructions
- Notes
- Image URL (optional)

**Example:**
```
📝 MANUALLY ADD RECIPE
================================================================================

Recipe Title: Grandma's Apple Pie

Available categories: meal, side, dessert, breakfast, snack, drink
Category (or press Enter for 'meal'): dessert

Source/URL (optional, press Enter to skip): Family cookbook

Servings (e.g., '4 servings' or '8 cookies'): 8 slices

Total cook time (e.g., '30 mins' or '1 hour'): 1 hour 30 mins

📋 Ingredients:
Enter ingredients one per line. Press Enter on empty line when done.
  1. 6 cups sliced apples
  2. 1 cup sugar
  3. 2 tablespoons flour
  4. 1 teaspoon cinnamon
  5. 2 pie crusts
  6. 

📝 Instructions:
Enter instructions. You can use multiple lines.
Type 'DONE' on a new line when finished.
Mix apples, sugar, flour, and cinnamon.
Pour into pie crust.
Cover with top crust and seal edges.
Bake at 375°F for 45-50 minutes.
DONE

💭 Notes (optional): Best served warm with vanilla ice cream

Image URL (optional): 

✅ Added 'Grandma's Apple Pie' to your recipe collection!
```

### List All Recipes

```bash
# List all recipes
python recipe_manager.py list

# List recipes by category
python recipe_manager.py list meal
python recipe_manager.py list dessert
python recipe_manager.py list breakfast
```

**Example output:**
```
📚 All Recipes (12 total):
================================================================================
1. Easy Meatloaf
   Category: meal | Cook Time: 1 hour 15 mins | Servings: 8 servings
   URL: https://www.allrecipes.com/recipe/16354/easy-meatloaf/

2. Chocolate Chip Cookies
   Category: dessert | Cook Time: 30 mins | Servings: 48 cookies
   URL: https://cooking.nytimes.com/recipes/1015987-chocolate-chip-cookies
   Notes: Holiday favorite
```

### Generate Meal Plan

Randomly select meals for your week and get a shopping list:

```bash
# Generate a 3-meal plan (default)
python recipe_manager.py plan

# Generate a 5-meal plan
python recipe_manager.py plan 5

# Generate a 7-meal plan (one for each day)
python recipe_manager.py plan 7
```

**Example output:**
```
🍽️  YOUR 3-MEAL WEEKLY PLAN
================================================================================

Meal 1: Easy Meatloaf
  Cook Time: 1 hour 15 mins | Servings: 8 servings
  URL: https://www.allrecipes.com/recipe/16354/easy-meatloaf/

Meal 2: Chicken Stir Fry
  Cook Time: 25 mins | Servings: 4 servings
  URL: https://www.foodnetwork.com/recipes/...

Meal 3: Spaghetti Carbonara
  Cook Time: 30 mins | Servings: 6 servings
  URL: https://www.seriouseats.com/recipes/...

💡 Generating shopping list...

================================================================================
🛒 CONSOLIDATED SHOPPING LIST
================================================================================

📋 Ingredients Needed:

1. 2 pounds ground beef
2. 1 onion, chopped
3. 2 eggs
4. 1 cup breadcrumbs
5. 2 tablespoons olive oil
6. 1 pound chicken breast
7. 3 cups mixed vegetables
8. 1/4 cup soy sauce
...

================================================================================
Total ingredient items: 28
================================================================================
```

### Search Recipes

Search by recipe title or ingredient:

```bash
# Search for chicken recipes
python recipe_manager.py search chicken

# Search for recipes with chocolate
python recipe_manager.py search chocolate

# Search for specific recipe
python recipe_manager.py search "apple pie"
```

## 🌐 Supported Recipe Websites

The tool uses the `recipe-scrapers` library which supports 100+ websites including:

- AllRecipes
- Food Network
- NYT Cooking
- Serious Eats
- Bon Appétit
- Epicurious
- Tasty
- BBC Food
- Delish
- Martha Stewart
- Simply Recipes
- Cookie and Kate
- And many more!

[Full list of supported sites](https://github.com/hhursev/recipe-scrapers#scrapers-available-for)

## 📂 File Structure

```
recipe-manager/
├── recipe_manager.py     # Main Python script
├── recipes.csv           # Your recipe database (created automatically)
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🗃️ Data Storage

Recipes are stored in `recipes.csv` with the following fields:
- **title** - Recipe name
- **url** - Source URL or identifier
- **category** - meal, side, dessert, etc.
- **ingredients** - JSON array of ingredients
- **instructions** - Step-by-step instructions
- **cook_time** - Total cooking time
- **servings** - Number of servings
- **image_url** - Recipe image URL
- **notes** - Your personal notes

You can manually edit `recipes.csv` with Excel, Numbers, or any text editor.

## 📱 Categories

Default categories:
- `meal` - Main dishes
- `side` - Side dishes
- `dessert` - Desserts
- `breakfast` - Breakfast items
- `snack` - Snacks
- `drink` - Beverages

You can create custom categories by typing a new category name when adding a recipe!

## 🔧 Advanced Usage

### Backup Your Recipes

Simply copy the `recipes.csv` file:

```bash
cp recipes.csv recipes_backup_$(date +%Y%m%d).csv
```

### Export to Excel

The CSV file can be opened directly in Excel, Google Sheets, or Numbers.

### Bulk Import

You can add multiple recipes to `recipes.csv` manually or via script and they'll be available immediately.

## 🐛 Troubleshooting

### Recipe scraper not working?

- Verify the URL is correct and accessible
- Check if the website is in the [supported sites list](https://github.com/hhursev/recipe-scrapers#scrapers-available-for)
- Use `manual` mode to add the recipe manually if scraping fails

### Dependencies not installing?

Try upgrading pip first:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Recipe site not supported?

Use the manual entry feature:
```bash
python recipe_manager.py manual
```

## 🤝 Contributing

Found a bug or have a feature request? Open an issue on GitHub!

## 📄 License

MIT License - Feel free to use this for personal or commercial projects.

## 🙏 Acknowledgments

- [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) - Amazing library for scraping recipes
- [pandas](https://pandas.pydata.org/) - Data manipulation
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

**Happy cooking! 🍽️**
