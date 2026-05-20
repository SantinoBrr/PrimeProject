"""
StyleSense — Setup Script
Verifica el entorno, instala dependencias y crea el .env
"""
import subprocess
import sys
import os
import shutil


def run(cmd, check=True):
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        sys.exit(1)
    return result


def main():
    print("\n" + "=" * 60)
    print("  StyleSense — Setup")
    print("=" * 60 + "\n")

    # Python version check
    version = sys.version_info
    if version < (3, 9):
        print("ERROR: Se requiere Python 3.9 o superior.")
        print(f"  Versión actual: {version.major}.{version.minor}")
        sys.exit(1)
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")

    # pip check
    result = run("pip --version", check=False)
    if result.returncode != 0:
        print("ERROR: pip no está disponible.")
        sys.exit(1)
    print("✓ pip disponible")

    # Install requirements
    print("\nInstalando dependencias...")
    run("pip install -r requirements.txt")
    print("✓ Dependencias instaladas")

    # Create .env if not exists
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("\n✓ Archivo .env creado desde .env.example")
        else:
            with open(".env", "w") as f:
                f.write("ANTHROPIC_API_KEY=\nSUPABASE_URL=\nSUPABASE_ANON_KEY=\nSUPABASE_SERVICE_ROLE_KEY=\nSUPABASE_JWT_SECRET=\nFLASK_SECRET_KEY=change-me\nFLASK_DEBUG=true\n")
            print("\n✓ Archivo .env creado")
        print("  ⚠  IMPORTANTE: editá el archivo .env con tus credenciales antes de iniciar.")
    else:
        print("\n✓ Archivo .env ya existe")

    print("\n" + "=" * 60)
    print("  ¡Setup completado!")
    print("=" * 60)
    print("""
Pasos siguientes:
  1. Editá el archivo .env con tus claves de API:
     - ANTHROPIC_API_KEY  → https://console.anthropic.com
     - SUPABASE_URL       → Supabase > Project Settings > API
     - SUPABASE_ANON_KEY  → Supabase > Project Settings > API
     - SUPABASE_SERVICE_ROLE_KEY → mismo lugar
     - SUPABASE_JWT_SECRET → Supabase > Project Settings > API > JWT Settings

  2. Ejecutá el SQL en Supabase:
     - Copiá el contenido de setup_db.sql
     - Pegalo en Supabase > SQL Editor > New query
     - Ejecutá

  3. Iniciá la aplicación:
     python app.py

  4. Abrí en el navegador:
     http://localhost:5000
""")


if __name__ == "__main__":
    main()
