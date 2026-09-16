# TTRPG Card Generator

A fully local tool for generating custom, printable reference cards for TTRPGs. This tool is designed to work with datasets that follow the 5etools JSON structure.

Whether you need spell cards, item cards, class features, or many others, this generator automatically formats your dataset into clean, readable cards ready for the table (allegedly).

##  Features

* **Smart Prioritization:** Built with various rulesets in mind. If a specific source is prioritized (like a newer core book), the generator will intelligently select the most relevant version while filtering out redundant duplicates.
* **Interactive Web UI:** Provides a sleek local web interface to easily select your desired datasets and apply specific subset filters like spell level, item rarity, or requirements.
* **Custom Visual Overrides:** Easily swap out card backgrounds, watermarks, and card backs. The UI automatically scans your `icons` folder for available SVGs to choose from, or you can upload your own custom `.svg` files directly through the web interface.
* **Printable Card Backs:** Generate perfectly sized, 3x3 grid pages of card backs with a single click, ready to be printed on the reverse side of your decks.
* **Dynamic Formatting:** Don't worry about long text walls. The engine intelligently calculates text length and table sizes, automatically splitting massive class features or complex spell descriptions across multiple consecutive cards.
* **Zero Dependencies Required:** You don't need Python or Git installed on your system. The installer automatically downloads a portable, isolated Python 3.14 environment specifically for this tool.
* **Always Up to Date:** The installer sets up the environment, and the launcher allows you to pull the latest data from your chosen source.

##  Installation

This tool is designed to run on **Windows** and requires an active internet connection for the initial setup.

1. Download **`install.bat`** and run it.
2. The installer will set up a portable Python environment.
3. Once finished, it will launch the **TTRPG Card Generator Setup**.
4. Provide a Git URL or a local ZIP path to your data source.
5. Use **`launch.bat`** anytime to start the generator.

##  How to Use

1. Double-click **`launch.bat`**. This will start the local server and automatically open the Controller UI in your default web browser.
2. **Select Datasets:** Check the boxes for the datasets you want to include.
3. **Apply Filters:** When you select a dataset, subset filters will appear. Use these to narrow down your deck (e.g., only generate Level 1-3 spells, or only items with a certain rarity and requirements).
4. **Customize Visuals (Optional):** Use the Visual Options panel to select different backgrounds, watermarks, or card backs from your `icons` folder, or upload your own custom `.svg` files to override the defaults.
5. Click **Generate Deck** to create your cards.
6. Once complete, click the **Open Custom Deck** button. Your cards will open in a new tab as `Custom_Deck_Cards.html`.
7. **Generate Card Backs (Optional):** Need backs for your printed cards? Click **Generate Backs** to create a printable 3x3 grid of your selected card back design.

##  Printing Instructions
The output HTML is optimized for standard US Letter (8.5" x 11") printing.
* Press `Ctrl + P` in your browser.
* Set Paper Size to **Letter**.
* Set Margins to **None**.
* Make sure **Background graphics** are enabled so the card borders and icons print correctly.
* Save to PDF (might take a long time or timeout, depending on how many cards are being generated and printed at once) or print directly to cardstock!

##  Troubleshooting

**Data source not detected / dataset files 404:**
The launcher looks under `generators/` for a 5eTools-shaped tree (`data/class` and `data/spells`), not a specific folder name. `generators/data` is preferred when that tree is ready; otherwise the first alphabetically named ready child (for example `generators/5etools`) is used. Git/ZIP installs still land in `generators/data` by default.

**"ModuleNotFoundError" when launching:**
Make sure you ran `install.bat` completely. If you are updating from an older version, delete the `python-env` folder and run `install.bat` again to pull the correct environment.

**Cards are clipping or overflowing:**
The engine attempts to auto-scale fonts, but very dense tables might still push limits. Check the generated HTML to see how the engine chunked the data.

##  Tips, if you feel like it

**ko-fi.com/bankenichi**