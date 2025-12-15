# JP Leftover Hunter v4.2

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyQt5](https://img.shields.io/badge/PyQt5-GUI-brightgreen.svg)](https://riverbankcomputing.com/software/pyqt/)

A powerful tool to automatically check the quality of machine-translated visual novel scripts. It finds common errors, leftover Japanese text, and other weird stuff, saving you hours of boring manual work.

![Screenshot of the Application](https://i.imgur.com/your-screenshot-image-link.png) <!-- Replace with your app's screenshot link -->

## 🌟 Cool Features

-   **🧠 Smart Line Matching:**
    -   Stops relying on line numbers that are always messed up after translation.
    -   Understands common line markers like `p1`, `p2`, `l1`, etc.
    -   If there are no markers, it uses a clever content-similarity trick to match the right lines together.

-   **⚡ Blazing Fast Scanning:**
    -   Processes multiple files at the same time (multi-threading).
    -   Cuts down scanning time from hours to just a few minutes, even for huge projects.

-   **💾 Smart Translation Cache:**
    -   Remembers translations from DeepL/Google Translate in a file.
    -   The next time you scan, it won't re-translate the same sentence. It's instant.

-   **🔍 Finds All the Common Problems:**
    -   **Not Translated:** Catches empty lines that were skipped.
    -   **JP Chars Leftover:** Spots Japanese characters (Hiragana, Katakana, Kanji) that weren't translated.
    -   **Pronoun Errors:** Flags things like translating '彼女' (she) as 'he'.
    -   **Anomalous Symbols:** Finds weird symbols like `[]` or `"""` that are out of place.
    -   **Too Formal:** Points out words like "therefore" or "henceforth" that sound unnatural in dialogue.

-   **💡 Gives You Better Translations:**
    -   For every problem it finds, it automatically suggests a better translation using DeepL/Google Translate.

-   **🖥️ Easy-to-Use Interface:**
    -   A clean table shows you all the problems, with the bad parts highlighted.
    -   Use filters to only see specific errors (e.g., only "Pronoun Errors").
    -   Export all the findings to a `.csv` file with one click.

## 🤔 Why This Tool?

Let's be real, manual QC sucks. It's boring, takes forever, and you'll always miss something. This tool does the soul-crushing part for you. It finds the mistakes so you can focus on actually improving the translation and making it sound good.

## 📁 What It Works With

This is built mainly for the **Kirikiri/Kirikiri2 Engine**, but it's flexible enough for other text-based scripts.

-   **File Extensions:** `.ks`, `.tjs`, `.txt`, `.ks.scn`, `.txt.scn`
-   **Line Marker Patterns It Knows:**
    -   `p1`, `p2`, `p3`, ...
    -   `l1`, `l2`, `l3`, ...
    -   `msg1`, `dialog1`, `line1`, etc.
    -   And formats like: `[p1]`, `// p1:`, `p1 =`, and so on.

## 🚀 How to Get It Running

### What You Need

-   Python 3.6 or newer.
-   `pip` (usually comes with Python).

### Steps

1.  **Clone the Repo:**
    ```bash
    git clone https://github.com/yourusername/JPLeftoverHunter.git
    cd JPLeftoverHunter
    ```

2.  **Install the Stuff It Needs:**
    Create a file named `requirements.txt` and paste this into it:
    ```
    PyQt5==5.15.9
    chardet==5.1.0
    deep-translator==1.11.4
    ```
    Then run this in your terminal:
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ How to Run the Tool

You have two options: run the script directly if you have Python, or build a standalone `.exe` file.

### Option A: Run the `.pyw` Script Directly

This is the quickest way if you already have Python and the dependencies installed.

1.  Make sure you've done the installation steps above.
2.  Open your terminal or command prompt in the project folder.
3.  Run this command:
    ```bash
    python JPLeftoverHunter.pyw
    ```

### Option B: Build a Standalone `.exe` with PyInstaller

This creates a single `.exe` file that you can share and run on any Windows machine, even without Python installed.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Build the Executable:**
    Run this command in your terminal from the project folder:
    ```bash
    pyinstaller --onefile --windowed --name="JP Leftover Hunter" JPLeftoverHunter.pyw
    ```
    *   `--onefile`: Packs everything into a single `.exe` file.
    *   `--windowed`: Runs the app without a black console window in the background.
    *   `--name="..."`: Sets the name of the final `.exe` file.

3.  **Find Your App:**
    After the process finishes, you'll find your `.exe` inside a new folder called `dist`.

## 📖 How to Use It

1.  **Get Your Folders Ready:**
    -   **JP Folder:** The original Japanese scripts.
    -   **MTL Folder:** The machine-translated scripts.

2.  **Open the App:** Run `JPLeftoverHunter.pyw` or the `.exe` you built.

3.  **Set It Up:**
    -   Click the 📁 button to select your **JP Folder**.
    -   Click the other 📁 button to select your **MTL Folder**.
    -   Choose the **Target Language** for suggestions (e.g., English or Indonesian).

4.  **Hit Scan:** Click the 🔍 button and grab a coffee. It'll be done before you know it.

5.  **Check the Results:**
    -   The table will fill up with every problem it found.
    -   Use the **Filter** dropdown to look at just one type of error.
    -   Hover over any cell to see more details.

6.  **Export:** Click the 💾 button to save everything to a `.csv` file.

## ⚙️ How It Works (The Gist)

1.  **Reads Files:** It reads all your scripts and pulls out only the dialogue, ignoring the engine's code.
2.  **Matches Lines:** It uses its smart matching logic to pair each Japanese line with its translated version.
3.  **Analyzes:** It checks each pair for all the common problems listed above, and it does this for many files at once.
4.  **Gets Suggestions:** If it finds a problem, it asks DeepL/Google for a better translation and saves the result.
5.  **Reports:** It shows you everything in a nice, clean table.

## 🤝 Want to Help?

Found a bug? Got a cool idea for a new feature? Pull requests and issues are welcome!

1.  Fork the project.
2.  Make a new branch for your feature (`git checkout -b feature/SomeCoolFeature`).
3.  Commit your changes (`git commit -m 'Add a cool feature'`).
4.  Push to your branch (`git push origin feature/SomeCoolFeature`).
5.  Open a Pull Request.

## 📄 License

This project is under the MIT License - check out the [LICENSE](LICENSE) file for the full text.

## 🙏 Thanks & Credits

-   Big thanks to the creators of the awesome libraries we use: **PyQt5**, **chardet**, and **deep-translator**.
-   Made with ❤️ for the visual novel translation community.
6.  **Export:** Click the 💾 button to save everything to a `.csv` file.

## ⚙️ How It Works (The Gist)

1.  **Reads Files:** It reads all your scripts and pulls out only the dialogue, ignoring the engine's code.
2.  **Matches Lines:** It uses its smart matching logic to pair each Japanese line with its translated version.
3.  **Analyzes:** It checks each pair for all the common problems listed above, and it does this for many files at once.
4.  **Gets Suggestions:** If it finds a problem, it asks DeepL/Google for a better translation and saves the result.
5.  **Reports:** It shows you everything in a nice, clean table.

## 🤝 Want to Help?

Found a bug? Got a cool idea for a new feature? Pull requests and issues are welcome!

1.  Fork the project.
2.  Make a new branch for your feature (`git checkout -b feature/SomeCoolFeature`).
3.  Commit your changes (`git commit -m 'Add a cool feature'`).
4.  Push to your branch (`git push origin feature/SomeCoolFeature`).
5.  Open a Pull Request.

## 📄 License

This project is under the MIT License - check out the [LICENSE](LICENSE) file for the boring details.

## 🙏 Thanks & Credits

-   Big thanks to the creators of the awesome libraries we use: **PyQt5**, **chardet**, and **deep-translator**.
-   Made with ❤️ for the visual novel translation community.
