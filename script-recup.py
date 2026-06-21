import os

# 1. Extensions de code importantes à capturer
ALLOWED_EXTENSIONS = {'.py', '.tsx', '.ts', '.jsx', '.js'}

# 2. Dossiers lourds ou générés à ignorer absolument (partout dans l'arborescence)
IGNORED_DIRS = {'node_modules', 'venv', '.venv', '.git', '__pycache__', 'dist', 'build', '.next'}

# 3. Fichiers spécifiques inutiles pour l'IA à exclure
IGNORED_FILES = {
    'next-env.d.ts',       # Fichier de types automatique Next.js
    'generate_context.py', # S'exclure soi-même
    'script-recup.py',     # Exclure l'ancien script
    '__init__.py',         # Fichiers d'initialisation Python souvent vides
    'test_app.py'          # Fichiers de tests unitaires
}

OUTPUT_FILE = "context_notebooklm.txt"

def should_ignore_dir(path):
    """Vérifie si le chemin contient un dossier à ignorer."""
    parts = path.split(os.sep)
    return any(ignored in parts for ignored in IGNORED_DIRS)

def generate_context():
    total_files = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # En-tête global pour NotebookLM
        outfile.write("# PROJECT CONTEXT FOR NOTEBOOKLM\n")
        outfile.write("This file contains the layout and clean source code of important files.\n")
        outfile.write("=" * 80 + "\n\n")
        
        for root, dirs, files in os.walk('.'):
            # Élagage des dossiers cachés ou à ignorer pour accélérer le scan
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in IGNORED_DIRS]
            
            if should_ignore_dir(root):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Validation des critères d'exclusion
                if ext not in ALLOWED_EXTENSIONS:
                    continue
                if file in IGNORED_FILES:
                    continue
                if not os.path.exists(file_path):
                    continue
                if os.path.getsize(file_path) == 0:  # Ignore les fichiers vides
                    continue
                        
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                    
                    # Structuration du fichier dans le document final
                    outfile.write(f"### FILE: {file_path}\n")
                    outfile.write("-" * 40 + "\n")
                    outfile.write(content)
                    outfile.write("\n\n" + "=" * 80 + "\n\n")
                    
                    print(f"📦 Inclus : {file_path}")
                    total_files += 1
                    
                except Exception as e:
                    print(f"❌ Erreur lecture {file_path}: {e}")

    print(f"\n✅ Nettoyage terminé ! {total_files} fichiers essentiels condensés dans '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    generate_context()