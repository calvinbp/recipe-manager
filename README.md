# 🍳 Recipe Manager

A Python command-line tool to collect, organize, and manage your recipes. Automatically scrape recipes from websites, manually add family recipes, generate random meal plans, and create consolidated shopping lists.

## ✨ Features

- 🌐 **Auto-scrape recipes** from 100+ popular recipe websites (AllRecipes, NYT Cooking, Food Network, etc.)
- ✍️ **Manually add recipes** from cookbooks, family recipes, or handwritten notes
- 📄 **Bulk import from text files** - Import multiple recipes at once from a formatted .txt file
- ✏️ **Update existing recipes** - Edit any field of previously added recipes
- 📊 **Categorize recipes** (meal, side, dessert, breakfast, snack, drink, sauce, dressing, baked good, appetizer, condiment, base/component, other, or custom categories)
- 🎲 **Random meal planning** - Generate weekly meal plans with X number of meals
- 🛒 **Smart shopping lists** - Automatically consolidate ingredients (e.g., "1 C flour" + "2 C flour" = "3 C flour")
- 🔍 **Search functionality** - Find recipes by title or ingredient
- 💾 **Simple CSV storage** - Easy to backup and edit manually if needed
- 📝 **Add personal notes** to any recipe
- ✅ **Standardized ingredient format** - Uniform units and capitalization for consistency

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
- Ingredients (one per line with standardized format)
- Instructions
- Notes
- Image URL (optional)

#### Ingredient Format

When entering ingredients, use this format: `[quantity] [unit] [ingredient name]`

**Valid units:**
- **Volume:** `t` (tsp), `T` (Tbsp), `C` (cup), `ml`, `L`, `floz` (fl oz)
- **Weight:** `oz`, `lb`, `g`, `kg`
- **Counting:** `slice`, `slices`, `piece`, `pieces`, `clove`, `cloves`, `whole`, `each`, `can`, `cans`, `bunch`, `head`, `stalk`, `stalks`, `pkg`, `package`, `container`, `jar`, `box`
- **No unit:** For items like eggs, just use the count: `3 eggs`

**Examples:**
- `1/2 C cottage cheese` → Parsed as: 0.5 cup Cottage Cheese
- `2 T butter` → Parsed as: 2 Tbsp Butter
- `3 eggs` → Parsed as: 3 Eggs (no unit)
- `1 1/2 t vanilla` → Parsed as: 1.5 tsp Vanilla
- `2 slices bread` → Parsed as: 2 slices Bread
- `1 can tomatoes` → Parsed as: 1 can Tomatoes
- `3 cloves garlic` → Parsed as: 3 cloves Garlic
- `1/4 bunch cilantro` → Parsed as: 0.25 bunch Cilantro

The system will:
- Parse fractions and decimals
- Standardize unit abbreviations
- Capitalize ingredient names
- Allow consolidation in shopping lists

**Example session:**
```
MANUALLY ADD RECIPE
================================================================================

Recipe Title: Cottage Cheese Flatbread

Available categories: meal, side, dessert, breakfast, snack, drink, sauce, dressing, baked good, appetizer, condiment, base/component, other
Category (or press Enter for 'meal'): baked good

Source/URL (optional, press Enter to skip): tastyhappy.com

Servings (e.g., '4 servings' or '8 cookies'): 4 flatbreads

Total cook time (e.g., '30 mins' or '1 hour'): 15 mins

Ingredients:
Enter ingredients one per line. Press Enter on empty line when done.
Examples: '1/2 C cottage cheese', '2 T butter', '3 eggs'
Valid units: t, T, C, oz, floz, lb, g, kg, ml, L

Ingredient 1:
Ingredient: 1 C cottage cheese
  -> Added: 1 cup Cottage Cheese

Ingredient 2:
Ingredient: 1 egg
  -> Added: 1 Egg

Ingredient 3:
Ingredient: 1/2 t salt
  -> Added: 0.5 tsp Salt

Ingredient 4:
Ingredient: 2 slices bread
  -> Added: 2 slices Bread

Ingredient 5:
Ingredient: [press Enter to finish]
```
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

### Import Recipes from Text File

Bulk import multiple recipes from a `.txt` file - great for typing up recipes from cookbooks or family collections!

```bash
python recipe_manager.py import-txt my_recipes.txt
```

#### Text File Format

See `recipe_template.txt` for examples. Format for each recipe:

```
Title: Recipe Name
Category: category name
Servings: amount
Cook Time: time
Source: url or reference (optional)

Ingredients:
1/2 C ingredient one
2 T ingredient two
3 ingredient three

Instructions:
Step one instructions.
Step two instructions.
Step three instructions.

Notes: Optional notes here

*****
```

**Rules:**
- **Required fields:** Title, Ingredients, Instructions
- **Optional fields:** Category (defaults to 'meal'), Servings, Cook Time, Source, Notes
- **Separator:** Five asterisks (`*****`) between recipes
- **Ingredients:** Use standardized format (see ingredient format section above)
- **Blank lines:** Used to separate sections

**Example import:**

```bash
python recipe_manager.py import-txt recipe_template.txt
```

Output:
```
Importing recipes from: recipe_template.txt
================================================================================

Processing recipe 1...
  SUCCESS: Added 'Cottage Cheese Flatbread'
    Category: baked good | Ingredients: 4

Processing recipe 2...
  SUCCESS: Added 'Basic Pie Crust'
    Category: base/component | Ingredients: 5

================================================================================
Import complete: 2 successful, 0 failed
================================================================================
```

### Update Existing Recipe

Edit any field of an existing recipe:

```bash
# Update specific recipe by title
python recipe_manager.py update "Cottage Cheese Flatbread"

# Or browse and select from all recipes
python recipe_manager.py update
```

**Interactive process:**
1. Select recipe (if multiple matches or no title provided)
2. See current value for each field
3. Press Enter to keep current value, or type new value
4. Choose whether to update ingredients or instructions
5. Recipe is saved with changes

**Example session:**
```
UPDATING: Cottage Cheese Flatbread
================================================================================
Press Enter to keep current value, or type new value

Title [Cottage Cheese Flatbread]: 
Category [snack]: baked good
Servings [4 flatbreads]: 
Cook Time [15 mins]: 
Source/URL [tastyhappy.com]: 

Current Ingredients:
  1. 1 cup Cottage Cheese
  2. 1 Egg
  3. 0.5 tsp Salt

Update ingredients? (y/n): n

Current Instructions: Mix all ingredients...
Update instructions? (y/n): n

Notes []: Great for meal prep!

================================================================================
SUCCESS: Updated 'Cottage Cheese Flatbread'!
================================================================================
```

### List All Recipes

```bash
# List all recipes
python recipe_manager.py list

# List recipes by category
python recipe_manager.py list meal
python recipe_manager.py list dessert
python recipe_manager.py list "baked good"
python recipe_manager.py list "base/component"
python recipe_manager.py list sauce
```

**Available categories:** meal, side, dessert, breakfast, snack, drink, sauce, dressing, baked good, appetizer, condiment, base/component, other

**Category examples:**
- **base/component** - Pie crust, pizza dough, pasta dough, pie filling, stock/broth, bread dough
- **baked good** - Muffins, cookies, cakes, flatbreads
- **sauce** - Pasta sauce, gravy, marinara
- **condiment** - Spreads, dips, relishes

**Note:** You can also type any custom category when adding a recipe, and it will be added to your personal category list.

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
