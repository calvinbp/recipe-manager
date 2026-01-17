# 🛠️ Setup Instructions

This guide will help you set up a Python virtual environment for the Recipe Manager project.

## Prerequisites

- **Python 3.7 or higher** (Python 3.8+ recommended)
- **pip** (usually comes with Python)

To check if you have Python installed:

```bash
python3 --version
# or
python --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

## 🚀 Quick Start

### Step 1: Navigate to the project directory

```bash
cd recipe-manager
```

### Step 2: Create a virtual environment

**macOS/Linux:**
```bash
python3 -m venv venv
```

**Windows:**
```bash
python -m venv venv
```

This creates a new directory called `venv` containing an isolated Python environment.

### Step 3: Activate the virtual environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

When activated, you should see `(venv)` at the beginning of your command prompt:
```
(venv) user@computer:~/recipe-manager$
```

### Step 4: Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs all required packages:
- `recipe-scrapers` - For scraping recipes from websites
- `pandas` - For data manipulation
- `requests` - For HTTP requests
- `beautifulsoup4` - For HTML parsing
- `pillow` - For image processing
- `pytesseract` - For OCR (if needed)

### Step 5: Verify installation

```bash
python recipe_manager.py
```

You should see the help menu with usage instructions.

## 📝 Detailed Instructions by Platform

### macOS

1. **Open Terminal** (Applications > Utilities > Terminal)

2. **Navigate to the project:**
   ```bash
   cd ~/path/to/recipe-manager
   ```

3. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

4. **Activate it:**
   ```bash
   source venv/bin/activate
   ```

5. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Linux (Ubuntu/Debian)

1. **Install Python and venv** (if not already installed):
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **Navigate to the project:**
   ```bash
   cd ~/path/to/recipe-manager
   ```

3. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

4. **Activate it:**
   ```bash
   source venv/bin/activate
   ```

5. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Windows

#### Using Command Prompt

1. **Open Command Prompt** (Win + R, type `cmd`, press Enter)

2. **Navigate to the project:**
   ```cmd
   cd C:\path\to\recipe-manager
   ```

3. **Create virtual environment:**
   ```cmd
   python -m venv venv
   ```

4. **Activate it:**
   ```cmd
   venv\Scripts\activate
   ```

5. **Install dependencies:**
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

#### Using PowerShell

1. **Open PowerShell**

2. **Navigate to the project:**
   ```powershell
   cd C:\path\to\recipe-manager
   ```

3. **Create virtual environment:**
   ```powershell
   python -m venv venv
   ```

4. **Activate it:**
   ```powershell
   venv\Scripts\Activate.ps1
   ```

   If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

5. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

## 🔄 Daily Usage

### Activating the virtual environment

Every time you want to use the Recipe Manager, activate the virtual environment first:

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### Deactivating the virtual environment

When you're done, you can deactivate it:

```bash
deactivate
```

### Running the Recipe Manager

Once the virtual environment is activated:

```bash
# Add a recipe from URL
python recipe_manager.py add "https://www.allrecipes.com/recipe/12345/"

# List all recipes
python recipe_manager.py list

# Generate a meal plan
python recipe_manager.py plan 5

# Search for recipes
python recipe_manager.py search chicken
```

## 🐛 Troubleshooting

### "python3: command not found" (macOS/Linux)

Try using `python` instead:
```bash
python -m venv venv
```

### "python: command not found" (Windows)

Make sure Python is installed and added to your PATH. Download from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during installation.

### "pip: command not found"

Try using:
```bash
python -m pip install -r requirements.txt
```

### Permission errors (macOS/Linux)

If you get permission errors, make sure you're not using `sudo`. Virtual environments should be created without sudo.

### Virtual environment not activating

Make sure you're in the project directory and the `venv` folder exists. If it doesn't, create it again:
```bash
python3 -m venv venv
```

### Import errors after installation

1. Make sure the virtual environment is activated (you should see `(venv)` in your prompt)
2. Try reinstalling dependencies:
   ```bash
   pip install --upgrade --force-reinstall -r requirements.txt
   ```

### Issues with pytesseract

`pytesseract` requires Tesseract OCR to be installed separately:

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install tesseract-ocr
```

**Windows:**
Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH.

Note: `pytesseract` is only needed if you're extracting recipes from images. You can skip it if you're only scraping from URLs.

## 📦 Alternative: Using pipenv or poetry

If you prefer using `pipenv` or `poetry` for dependency management:

### Using pipenv

```bash
pip install pipenv
pipenv install
pipenv shell
```

### Using poetry

```bash
pip install poetry
poetry install
poetry shell
```

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Virtual environment created (`venv` directory exists)
- [ ] Virtual environment activates without errors
- [ ] All dependencies installed (`pip list` shows required packages)
- [ ] Recipe Manager runs (`python recipe_manager.py` shows help menu)
- [ ] Can add a test recipe (optional)

## 🆘 Getting Help

If you encounter issues:

1. Make sure Python 3.7+ is installed
2. Verify the virtual environment is activated
3. Check that all dependencies are installed: `pip list`
4. Try reinstalling: `pip install --upgrade --force-reinstall -r requirements.txt`
5. Check the [README.md](README.md) for usage examples
