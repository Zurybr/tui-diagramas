#!/bin/bash
# Script de instalación para MD TUI en Termux/Ubuntu

set -e

echo "📝 MD TUI - Instalador"
echo "======================"
echo ""

# Detectar si es Termux
if [ -n "$TERMUX_VERSION" ]; then
    echo "📱 Detectado entorno Termux"
    IS_TERMUX=1
else
    echo "🖥️ Entorno estándar Linux"
    IS_TERMUX=0
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no encontrado. Instalando..."
    if [ $IS_TERMUX -eq 1 ]; then
        pkg update
        pkg install -y python
    else
        echo "Por favor instala Python3 manualmente"
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION detectado"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    echo "📦 Instalando pip..."
    python3 -m ensurepip --upgrade
fi

# Crear entorno virtual (opcional pero recomendado)
read -p "¿Crear entorno virtual? (recomendado) [Y/n]: " create_venv
if [[ ! $create_venv =~ ^[Nn]$ ]]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# ========== INSTALAR HERRAMIENTAS DE DIAGRAMAS ==========
echo ""
echo "🎨 Instalando renderizadores de diagramas..."

# D2 - Instalar desde releases oficiales
if ! command -v d2 &> /dev/null; then
    echo "  📦 Instalando D2..."
    D2_VERSION=$(curl -sL -A "Mozilla/5.0" "https://api.github.com/repos/terrastruct/d2/releases/latest" | grep '"tag_name"' | cut -d'"' -f4 | tr -d 'v')
    if [ -n "$D2_VERSION" ]; then
        TEMP_DIR=$(mktemp -d)
        curl -sL -A "Mozilla/5.0" "https://github.com/terrastruct/d2/releases/download/v${D2_VERSION}/d2-v${D2_VERSION}-linux-amd64.tar.gz" -o "$TEMP_DIR/d2.tar.gz"
        tar xzf "$TEMP_DIR/d2.tar.gz" -C "$TEMP_DIR"
        mkdir -p "$HOME/.local/bin"
        cp "$TEMP_DIR/d2-v${D2_VERSION}/bin/d2" "$HOME/.local/bin/d2"
        chmod +x "$HOME/.local/bin/d2"
        rm -rf "$TEMP_DIR"
        echo "  ✅ D2 instalado"
    else
        echo "  ⚠️ D2 no se pudo instalar"
    fi
else
    echo "  ✅ D2 ya instalado"
fi

# Diagon - Instalar desde PyPI
if ! command -v diagon &> /dev/null; then
    echo "  📦 Instalando Diagon..."
    pip install diagon --break-system-packages 2>/dev/null || pip install diagon
    if command -v diagon &> /dev/null; then
        echo "  ✅ Diagon instalado"
    else
        echo "  ⚠️ Diagon no se pudo instalar"
    fi
else
    echo "  ✅ Diagon ya instalado"
fi

# Mermaid CLI (opcional, requiere Node.js)
if ! command -v mmdc &> /dev/null; then
    if command -v npm &> /dev/null; then
        echo "  📦 Instalando Mermaid CLI..."
        npm install -g @mermaid-js/mermaid-cli 2>/dev/null || echo "  ⚠️ Error instalando mmdc"
    else
        echo "  ℹ️ Node.js no encontrado, omitiendo Mermaid CLI"
    fi
else
    echo "  ✅ Mermaid CLI ya instalado"
fi

# Hacer ejecutable el script
chmod +x mdtui.py

# Crear symlink en PATH
if [ $IS_TERMUX -eq 1 ]; then
    # Termux
    if [ -d "$PREFIX/bin" ]; then
        ln -sf $(pwd)/mdtui.py $PREFIX/bin/mdtui
        echo "✅ Comando 'mdtui' instalado en $PREFIX/bin"
    fi
else
    # Linux estándar
    if [ -d "$HOME/.local/bin" ]; then
        mkdir -p $HOME/.local/bin
        ln -sf $(pwd)/mdtui.py $HOME/.local/bin/mdtui
        echo "✅ Comando 'mdtui' instalado en $HOME/.local/bin"
        echo "   Asegúrate de tener $HOME/.local/bin en tu PATH"
    fi
fi

echo ""
echo "🎉 Instalación completada!"
echo ""
echo "Uso:"
echo "  mdtui              # Abre explorador en directorio actual"
echo "  mdtui archivo.md   # Abre archivo específico"
echo "  mdtui /ruta/dir    # Abre directorio específico"
echo ""
echo "Opcional - Instalar renderizadores de diagramas:"
echo "  # Mermaid (requiere Node.js)"
echo "  npm install -g @mermaid-js/mermaid-cli"
echo ""
echo "  # D2 (requiere Go)"
echo "  go install oss.terrastruct.com/d2@latest"
echo ""
echo "📖 Para ayuda dentro de la app, presiona '?' o 'h'"
