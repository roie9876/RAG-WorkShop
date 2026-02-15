# 🛠️ מדריך התקנת דרישות מוקדמות (Prerequisites)

> **מדריך צעד-אחר-צעד** להתקנת כל הכלים הנדרשים לסדנה.  
> בחרו את המערכת שלכם: [Windows](#-windows) | [macOS](#-macos)

---

## 📋 רשימת כלים נדרשים

| כלי | למה צריך אותו? | גרסה מינימלית |
|------|----------------|---------------|
| **VS Code** | עורך קוד – בו נעבוד לאורך כל הסדנה | Latest |
| **Python** | שפת התכנות של הסדנה | 3.11+ (עד 3.13) |
| **Git** | ניהול גרסאות – להוריד את חומרי הסדנה | Latest |
| **Azure CLI** | כלי שורת פקודה לניהול משאבי Azure | Latest |

---

## 🪟 Windows

### שלב 1: התקנת VS Code

1. גלשו ל-[https://code.visualstudio.com/download](https://code.visualstudio.com/download)
2. לחצו על **"Download for Windows"** (כפתור כחול גדול)
3. הריצו את קובץ ההתקנה (`VSCodeSetup-x64-*.exe`)
4. באשף ההתקנה:
   - ✅ סמנו **"Add to PATH"** (חשוב!)
   - ✅ סמנו **"Register Code as an editor for supported file types"**
   - ✅ סמנו **"Add 'Open with Code' action to Windows Explorer"**
5. לחצו **Install** ואז **Finish**

**בדיקה:** פתחו Terminal (חפשו "cmd" ב-Start) והקלידו:
```bash
code --version
```
אם מופיע מספר גרסה – ההתקנה הצליחה ✅

---

### שלב 2: התקנת Python

> ⚠️ **חשוב**: צריך Python 3.11 עד 3.13. **לא** להתקין 3.14 ומעלה.

1. גלשו ל-[https://www.python.org/downloads/](https://www.python.org/downloads/)
2. לחצו על **"Download Python 3.13.x"** (או 3.12/3.11)
3. הריצו את קובץ ההתקנה
4. **במסך הראשון של ההתקנה**:
   - ✅ **חובה לסמן: "Add python.exe to PATH"** (בתחתית המסך!)
   - לחצו **"Install Now"**

   ![Python PATH](https://docs.python.org/3/_images/win_installer.png)

5. בסיום – לחצו **"Disable path length limit"** (אם מופיע)
6. לחצו **Close**

**בדיקה:** פתחו Terminal **חדש** (חשוב – לסגור ולפתוח מחדש!) והקלידו:
```bash
python --version
```
צריך להופיע: `Python 3.11.x` / `Python 3.12.x` / `Python 3.13.x` ✅

> 💡 **בעיה נפוצה**: אם `python` לא מזוהה, נסו `python3` או `py` במקום.  
> אם זה עדיין לא עובד – חזרו לשלב ההתקנה ו**ודאו שסימנתם "Add to PATH"**.

---

### שלב 3: התקנת Git

1. גלשו ל-[https://git-scm.com/downloads/win](https://git-scm.com/downloads/win)
2. לחצו על **"Click here to download"** (הקישור העליון)
3. הריצו את קובץ ההתקנה
4. לחצו **Next** בכל המסכים (הגדרות ברירת המחדל מתאימות)
   - במסך **"Adjusting your PATH"** – ודאו שנבחר **"Git from the command line and also from 3rd-party software"**
5. לחצו **Install** ואז **Finish**

**בדיקה:** פתחו Terminal **חדש** והקלידו:
```bash
git --version
```
צריך להופיע: `git version 2.x.x` ✅

---

### שלב 4: התקנת Azure CLI

1. גלשו ל-[https://learn.microsoft.com/cli/azure/install-azure-cli-windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows)
2. לחצו על **"Latest release of the Azure CLI"** (להוריד את ה-MSI)
3. הריצו את קובץ ההתקנה (`azure-cli-*.msi`)
4. לחצו **Next** → **I accept** → **Install** → **Finish**

**בדיקה:** פתחו Terminal **חדש** והקלידו:
```bash
az --version
```
צריך להופיע גרסה ✅

**התחברות ל-Azure:**
```bash
az login
```
ייפתח דפדפן – התחברו עם חשבון Azure שלכם.

---

### שלב 5: התקנת תוספים ל-VS Code

פתחו VS Code ולחצו `Ctrl+Shift+X` (חלון Extensions), חפשו והתקינו:

| תוסף | חיפוש | למה? |
|-------|--------|------|
| **Python** | `ms-python.python` | תמיכה בפייתון |
| **Jupyter** | `ms-toolsai.jupyter` | הרצת notebooks |
| **Azure Account** | `ms-vscode.azure-account` | התחברות ל-Azure |

או הריצו בטרמינל:
```bash
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
code --install-extension ms-vscode.azure-account
```

---

### שלב 6: הורדת חומרי הסדנה

פתחו Terminal והריצו:
```bash
git clone https://github.com/roie9876/RAG-WorkShop.git
cd RAG-WorkShop
```

פתחו את התיקיה ב-VS Code:
```bash
code .
```

---

### שלב 7: יצירת סביבת Python וירטואלית והתקנת חבילות

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> 💡 **מה זה venv?** סביבה וירטואלית שמבודדת את החבילות של הסדנה מפייתון הגלובלי שלכם. כך לא נוצרים קונפליקטים עם פרויקטים אחרים.

**בדיקה:** בתוך הסביבה הוירטואלית, הריצו:
```bash
python -c "import openai; print('✅ All good!')"
```

---

## 🍎 macOS

### שלב 1: התקנת VS Code

1. גלשו ל-[https://code.visualstudio.com/download](https://code.visualstudio.com/download)
2. לחצו על **"Download for Mac"**
   - **Apple Silicon** (M1/M2/M3/M4) – בחרו **"Apple Silicon"**
   - **Intel** – בחרו **"Intel Chip"**
   - 💡 לא בטוחים? לחצו על  → **About This Mac** → חפשו "Chip"
3. פתחו את קובץ ה-`.zip` שהורדתם
4. גררו את **Visual Studio Code.app** לתיקיית **Applications**
5. פתחו את VS Code מ-Applications

**הוספת `code` לשורת הפקודה:**
1. פתחו VS Code
2. לחצו `Cmd+Shift+P` (Command Palette)
3. הקלידו: **"Shell Command: Install 'code' command in PATH"**
4. לחצו Enter

**בדיקה:** פתחו Terminal (חפשו "Terminal" ב-Spotlight עם `Cmd+Space`) והקלידו:
```bash
code --version
```

---

### שלב 2: התקנת Homebrew (מנהל חבילות)

> Homebrew מקל מאוד על התקנת כלים ב-Mac. **מומלץ מאוד**.

פתחו Terminal והריצו:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

עקבו אחרי ההוראות בטרמינל. בסיום, ייתכן שתצטרכו להריץ פקודה נוספת שמוצגת על המסך (מתחילה ב-`eval`).

**בדיקה:**
```bash
brew --version
```

---

### שלב 3: התקנת Python

> ⚠️ **חשוב**: macOS מגיע עם Python ישן. **צריך להתקין Python 3.11+**.

**אפשרות א׳ – עם Homebrew (מומלץ):**
```bash
brew install python@3.13
```

**אפשרות ב׳ – ידנית:**
1. גלשו ל-[https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/)
2. הורידו את **macOS 64-bit universal2 installer**
3. הריצו את קובץ ה-`.pkg` ועברו את אשף ההתקנה

**בדיקה:**
```bash
python3 --version
```
צריך להופיע: `Python 3.11.x` / `Python 3.12.x` / `Python 3.13.x` ✅

> 💡 ב-Mac הפקודה היא `python3` (לא `python`).

---

### שלב 4: התקנת Git

**אפשרות א׳ – עם Homebrew:**
```bash
brew install git
```

**אפשרות ב׳ – התקנה אוטומטית:**

Git מותקן אוטומטית עם Xcode Command Line Tools. פשוט הריצו:
```bash
git --version
```
אם Git לא מותקן, macOS יציע להתקין אוטומטית – לחצו **Install**.

---

### שלב 5: התקנת Azure CLI

**עם Homebrew (מומלץ):**
```bash
brew install azure-cli
```

**בדיקה:**
```bash
az --version
```

**התחברות ל-Azure:**
```bash
az login
```
ייפתח דפדפן – התחברו עם חשבון Azure שלכם.

---

### שלב 6: התקנת תוספים ל-VS Code

פתחו VS Code ולחצו `Cmd+Shift+X` (חלון Extensions), חפשו והתקינו:

| תוסף | חיפוש | למה? |
|-------|--------|------|
| **Python** | `ms-python.python` | תמיכה בפייתון |
| **Jupyter** | `ms-toolsai.jupyter` | הרצת notebooks |
| **Azure Account** | `ms-vscode.azure-account` | התחברות ל-Azure |

או הריצו בטרמינל:
```bash
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
code --install-extension ms-vscode.azure-account
```

---

### שלב 7: הורדת חומרי הסדנה

```bash
git clone https://github.com/roie9876/RAG-WorkShop.git
cd RAG-WorkShop
```

פתחו את התיקיה ב-VS Code:
```bash
code .
```

---

### שלב 8: יצירת סביבת Python וירטואלית והתקנת חבילות

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**בדיקה:**
```bash
python3 -c "import openai; print('✅ All good!')"
```

---

## ✅ בדיקה סופית – הכל מותקן?

הריצו את הפקודות הבאות בטרמינל (בתוך הסביבה הוירטואלית):

```bash
# בדיקת כלים
echo "=== Checking Tools ==="
code --version && echo "✅ VS Code" || echo "❌ VS Code"
python3 --version && echo "✅ Python" || echo "❌ Python"  
git --version && echo "✅ Git" || echo "❌ Git"
az --version 2>/dev/null | head -1 && echo "✅ Azure CLI" || echo "❌ Azure CLI"

# בדיקת חבילות Python
echo ""
echo "=== Checking Python Packages ==="
python3 -c "import openai; print('✅ openai')" 2>/dev/null || echo "❌ openai"
python3 -c "import azure.identity; print('✅ azure-identity')" 2>/dev/null || echo "❌ azure-identity"
python3 -c "import azure.search.documents; print('✅ azure-search-documents')" 2>/dev/null || echo "❌ azure-search-documents"
```

אם כל הבדיקות עוברות – אתם מוכנים! 🎉

המשיכו ל-[setup.ipynb](setup.ipynb) להקמת משאבי Azure.

---

## ❓ פתרון בעיות נפוצות

### "python" / "python3" לא מזוהה (Windows)
- ודאו שסימנתם **"Add to PATH"** בהתקנה
- סגרו את ה-Terminal ופתחו מחדש
- נסו `py` במקום `python`

### "python" מריץ Python 2 (macOS)
- השתמשו ב-`python3` במקום `python`
- ודאו שההתקנה החדשה קיימת: `which python3`

### "pip" לא מזוהה
- נסו `pip3` במקום `pip`
- או: `python3 -m pip install -r requirements.txt`

### VS Code לא מזהה את Python
1. פתחו VS Code
2. `Ctrl+Shift+P` (Windows) / `Cmd+Shift+P` (Mac)
3. הקלידו: **"Python: Select Interpreter"**
4. בחרו את Python מהסביבה הוירטואלית (`.venv`)

### שגיאת הרשאות ב-macOS
- הוסיפו `sudo` לפני הפקודה, למשל: `sudo pip3 install -r requirements.txt`
- או עדיף: השתמשו בסביבה וירטואלית (`python3 -m venv .venv`)

### Azure CLI – "az login" נכשל
- ודאו שיש לכם חשבון Azure פעיל
- נסו: `az login --use-device-code` (שימושי אם הדפדפן לא נפתח)

### שגיאות בהתקנת חבילות (`pip install`)
- ודאו שאתם בסביבה וירטואלית (מופיע `(.venv)` בתחילת השורה)
- עדכנו pip: `pip install --upgrade pip`
- אם חבילה ספציפית נכשלת – נסו להתקין אותה בנפרד

---

## 🆘 עדיין נתקעים?

פתחו Issue ב-GitHub: [https://github.com/roie9876/RAG-WorkShop/issues](https://github.com/roie9876/RAG-WorkShop/issues)

ציינו:
- מערכת הפעלה (Windows/Mac) + גרסה
- הפקודה שנכשלה
- הודעת השגיאה המלאה
