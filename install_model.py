import argostranslate.package

def install_model():
    print("🔄 Updating package index...")
    argostranslate.package.update_package_index()

    available_packages = argostranslate.package.get_available_packages()

    for pkg in available_packages:
        if pkg.from_code == "en" and pkg.to_code == "vi":
            print("⬇️ Downloading model...")
            download_path = pkg.download()

            print("📦 Installing model...")
            argostranslate.package.install_from_path(download_path)

            print("✅ Done!")
            return

    print("❌ Model EN → VI not found")

if __name__ == "__main__":
    install_model()