// Inicialización del Mapa
let mapa = L.map('map').setView([7.1193, -73.1227], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(mapa);

// Leyenda fija de niveles de riesgo. Los colores y porcentajes deben coincidir
// siempre con obtener_metadatos_riesgo() en app/api/services.py.
const leyendaRiesgo = L.control({ position: 'bottomright' });
leyendaRiesgo.onAdd = function () {
    const div = L.DomUtil.create('div', 'leyenda-riesgo');
    div.innerHTML = `
        <div class="leyenda-titulo">Riesgo de intervención (4 semanas)</div>
        <div class="leyenda-item"><span class="leyenda-color" style="background:#28a745;"></span>0–25% · Bajo</div>
        <div class="leyenda-item"><span class="leyenda-color" style="background:#ffc107;"></span>26–50% · Medio</div>
        <div class="leyenda-item"><span class="leyenda-color" style="background:#fd7e14;"></span>51–75% · Alto</div>
        <div class="leyenda-item"><span class="leyenda-color" style="background:#dc3545;"></span>76–100% · Crítico</div>
    `;
    return div;
};
leyendaRiesgo.addTo(mapa);

// Notificaciones no bloqueantes (reemplazan a los alert() nativos).
// tipo: "error" | "advertencia" | "info"
function mostrarToast(mensaje, tipo = "error", duracionMs = 6000) {
    const contenedor = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast toast-${tipo}`;
    toast.innerHTML = `<span>${mensaje}</span><button class="toast-cerrar" aria-label="Cerrar">✕</button>`;

    const quitar = () => toast.remove();
    toast.querySelector(".toast-cerrar").addEventListener("click", quitar);
    setTimeout(quitar, duracionMs);

    contenedor.appendChild(toast);
}

let datosUpgdGlobal = [];
let marcadoresLeaflet = [];

// Carga Inicial en Lote
async function consultarBackend() {
    // Las 17 UPGDs reales del dataset limpio (ver data/dataset_limpio.xlsx)
    const upgds17 = [
        "HOSPITAL LOCAL DEL NORTE",
        "CLINICA CHICAMOCHA SA",
        "FUNDACION OFTALMOLOGICA DE SDER FOSCAL",
        "CLINICA MATERNO INFANTEL SAN LUIS SA",
        "UIMIST",
        "SALUD TOTAL EPS UUBC",
        "CORPORACION IPS SALUDCOOP BUCARAMANGA",
        "LOS COMUNEROS HOSPITAL UNIVERSITARIO DE BUCARAMANG",
        "SEDE GONZALEZ VALENCIA",
        "PUNTO VERDE COOMEVA",
        "SINERGIA GLOBAL EN SALUD SAS",
        "UNIDAD MEDICA QUIRURGICA COOMULTRASAN",
        "UNIDAD DE ATENCION PRIMARIA BUCARAMANGA",
        "IPS PUNTO DE SALUD",
        "SEDE AMBULATORIA BOLARQUI CLINICA CHICAMOCHA SA",
        "ASISTENCIA MÉDICA SAS",
        "ESE HOSPITAL UNIVERSITARIO DE SANTANDER"
    ];
    // Semana epidemiológica elegida por el usuario (1-52), validada antes de consultar
    const inputSemana = document.getElementById("inputSemana");
    let semanaElegida = parseInt(inputSemana.value, 10);
    if (isNaN(semanaElegida) || semanaElegida < 1 || semanaElegida > 52) {
        mostrarToast("La semana epidemiológica debe ser un número entre 1 y 52.", "advertencia");
        return;
    }
    inputSemana.value = semanaElegida;

    const payloadEnvio = upgds17.map(nombre => ({ "semana": semanaElegida, "nom_upgd": nombre }));

    const boton = document.querySelector(".btn-cargar");
    const textoOriginalBoton = boton.textContent;
    boton.disabled = true;
    boton.textContent = "Cargando...";

    try {
        const respuesta = await fetch("http://127.0.0.1:8000/api/v1/predict/bulk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payloadEnvio)
        });
        const res = await respuesta.json();
        if(res.status === "success") {
            datosUpgdGlobal = res.data;
            poblarListaUpgds();
            document.getElementById("inputBuscarUpgd").value = "";
            dibujarMarcadores();

            // Si alguna UPGD puntual no tenía datos para esta semana, se avisa
            // sin bloquear la carga de las demás.
            if (res.errores && res.errores.length > 0) {
                const nombres = res.errores.map(e => e.upgd).join(", ");
                mostrarToast(`No hay datos para la semana ${semanaElegida} en: ${nombres}. Se muestran las demás UPGD disponibles.`, "advertencia");
            }
        }
    } catch (e) {
        mostrarToast("Error al conectar al backend.", "error");
    } finally {
        boton.disabled = false;
        boton.textContent = textoOriginalBoton;
    }
}

// Renderizar círculos geográficos con Popups Dinámicos unificados
function dibujarMarcadores() {
    marcadoresLeaflet.forEach(m => {
        mapa.removeLayer(m.obj);
        if (m.iconoAlerta) mapa.removeLayer(m.iconoAlerta);
    });
    marcadoresLeaflet = [];

    datosUpgdGlobal.forEach(p => {
        // El relleno SIEMPRE refleja el mismo color de 4 niveles que el popup (contexto.color_hex),
        // calculado por el backend. Así el círculo y el texto "Nivel INS" nunca se contradicen.
        let circulo = L.circle([p.coordenadas.lat, p.coordenadas.lng], {
            radius: 380,
            weight: 2,
            fillColor: p.contexto.color_hex,
            color: p.contexto.color_hex,
            fillOpacity: 0.65
        }).addTo(mapa);

        // 🛠️ Corrección 4: Cambiado a "Riesgo estimado para las próximas 4 semanas"
        circulo.bindPopup(`
            <b style="font-size:1.1rem;">${p.upgd}</b><br>
            <span style="color:#666;">Horizonte: ${p.contexto.horizonte}</span><br>
            <hr style="margin:5px 0; border:0; border-top:1px solid #eee;">
            <b>Riesgo Estimado (4 Semanas):</b> ${(p.probabilidad_brote * 100).toFixed(1)}%<br>
            <b>Nivel INS:</b> <span style="color:${p.contexto.color_hex}; font-weight:bold;">${p.contexto.ins_nivel}</span>
            ${p.alerta ? `<hr style="margin:5px 0; border:0; border-top:1px solid #eee;">
            <span style="color:#b30000; font-weight:bold;">⚠ Alerta activa:</span> supera el umbral de acción calibrado durante 2 semanas consecutivas.` : ""}
        `);

        circulo.on('click', () => {

            solicitarExplicacionSHAP(p.upgd, p.semana_evaluada);
        });

        // El campo `alerta` del backend (umbral calibrado 0.12 + confirmación de 2 semanas)
        // es independiente del color de riesgo INS de arriba: puede haber una UPGD "verde"
        // (riesgo bajo según el color) que ya esté marcada con alerta real. Por eso se
        // superpone un ícono aparte, en vez de mezclarlo con el color.
        let iconoAlerta = null;
        if (p.alerta) {
            iconoAlerta = L.marker([p.coordenadas.lat, p.coordenadas.lng], {
                icon: L.divIcon({
                    className: 'icono-alerta-real',
                    html: '⚠',
                    iconSize: [20, 20],
                    iconAnchor: [10, 28]
                }),
                interactive: false
            }).addTo(mapa);
            iconoAlerta.bindTooltip("Alerta real activa (umbral calibrado + confirmación de 2 semanas)");
        }

        // 🛠️ Error 5: Guardamos de forma explícita p.probabilidad_brote
        marcadoresLeaflet.push({ obj: circulo, iconoAlerta: iconoAlerta, probabilidad: p.probabilidad_brote, colorBase: p.contexto.color_hex, nombre: p.upgd });
    });
}

// Interrogación a la API de SHAP y Actualización del Panel Explicativo (Sistema Experto)
async function solicitarExplicacionSHAP(nombre, semana) { // Quitamos datosVectoriales
    document.getElementById("contenidoSHAP").style.display = "none";
    document.getElementById("cargandoSHAP").style.display = "flex";

    try {
        const respuesta = await fetch("http://127.0.0.1:8000/api/v1/explain", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                "semana": semana,
                "nom_upgd": nombre
                // El backend debe buscar los vectores por su cuenta
            })
        });

        if (!respuesta.ok) {
            console.error(`Error HTTP ${respuesta.status}:`, respuesta.statusText);
            mostrarToast(`Error al obtener explicación: ${respuesta.status}`, "error");
            return;
        }

        const data = await respuesta.json();
        
        // ✅ Renderizar la respuesta SHAP en el panel
        document.getElementById("nombreUpgdSHAP").textContent = nombre;
        document.getElementById("txtSemanaActual").textContent = semana;
        document.getElementById("txtHorizonteTemporal").textContent = data.contexto.horizonte;
        
        // Círculo de porcentaje de riesgo
        const porcentaje = (data.riesgo * 100).toFixed(1);
        const circuloElem = document.getElementById("circuloPorcentaje");
        circuloElem.textContent = porcentaje + "%";
        circuloElem.style.backgroundColor = data.contexto.color_hex;
        
        // Información de contexto
        document.getElementById("txtEstadoRiesgo").textContent = data.contexto.estado;
        document.getElementById("txtNivelINS").textContent = data.contexto.ins_nivel;
        
        // ✅ Mostrar narrativa natural
        if (data.explicacion_natural) {
            const narrativaElem = document.getElementById("narrativaSHAP");
            narrativaElem.textContent = data.explicacion_natural;
            narrativaElem.style.display = "block";
        }
        
        // Lista de factores de impacto
        const listaFactoresElem = document.getElementById("listaFactores");
        listaFactoresElem.innerHTML = "";
        
        if (data.factores && data.factores.length > 0) {
            data.factores.forEach((factor, idx) => {
                const divFactor = document.createElement("div");
                divFactor.className = "factor-item";
                divFactor.style.marginBottom = "10px";
                
                const iconoTendencia = factor.es_aumento ? "📈" : "📉";
                const colorTendencia = factor.es_aumento ? "#dc3545" : "#28a745";
                
                divFactor.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <span style="font-weight: bold; color: ${colorTendencia};">${idx + 1}. ${factor.variable}</span>
                        <span style="font-size: 1.2rem;">${iconoTendencia}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #666;">
                        <span>${factor.peso_cualitativo}</span>
                        <span style="letter-spacing: 2px; color: ${colorTendencia};">${factor.barras}</span>
                    </div>
                    <div class="detalle-tecnico">${factor.detalle_tecnico}</div>
                `;
                listaFactoresElem.appendChild(divFactor);
            });
        }
        
        // Mostrar panel
        document.getElementById("contenidoSHAP").style.display = "block";

    } catch (e) {
        console.error("Error al procesar la explicabilidad:", e);
        mostrarToast("Error al obtener explicación: " + e.message, "error");
    } finally {
        document.getElementById("cargandoSHAP").style.display = "none";
    }
}

// Buscador de UPGD por nombre
// Llena el <datalist> con los nombres reales que devolvió el backend (sin duplicados).
function poblarListaUpgds() {
    const lista = document.getElementById("listaUpgds");
    lista.innerHTML = "";
    datosUpgdGlobal.forEach(p => {
        const opcion = document.createElement("option");
        opcion.value = p.upgd;
        lista.appendChild(opcion);
    });
}

// Se dispara con cada tecla escrita en el buscador. Si el texto coincide EXACTO
// con una UPGD (lo cual pasa apenas la seleccionás de la lista desplegable),
// filtra el mapa para mostrar solo esa institución. Si el campo queda vacío,
// vuelve a mostrar todas.
function onBuscarUpgd() {
    const texto = document.getElementById("inputBuscarUpgd").value.trim();

    if (texto === "") {
        filtrarPorUpgd(null);
        return;
    }

    const coincidencia = datosUpgdGlobal.find(
        p => p.upgd.toLowerCase() === texto.toLowerCase()
    );
    if (coincidencia) {
        filtrarPorUpgd(coincidencia.upgd);
    }
}

function limpiarFiltroUpgd() {
    document.getElementById("inputBuscarUpgd").value = "";
    filtrarPorUpgd(null);
}

// nombreExacto === null → muestra todas las UPGD.
// nombreExacto === "X" → deja solo el círculo de "X" en el mapa y centra la vista ahí.
function filtrarPorUpgd(nombreExacto) {
    marcadoresLeaflet.forEach(m => {
        const debeMostrarse = (nombreExacto === null) || (m.nombre === nombreExacto);
        if (debeMostrarse) {
            if (!mapa.hasLayer(m.obj)) m.obj.addTo(mapa);
            if (m.iconoAlerta && !mapa.hasLayer(m.iconoAlerta)) m.iconoAlerta.addTo(mapa);
        } else {
            if (mapa.hasLayer(m.obj)) mapa.removeLayer(m.obj);
            if (m.iconoAlerta && mapa.hasLayer(m.iconoAlerta)) mapa.removeLayer(m.iconoAlerta);
        }
    });

    if (nombreExacto !== null) {
        const marcador = marcadoresLeaflet.find(m => m.nombre === nombreExacto);
        if (marcador) {
            mapa.setView(marcador.obj.getLatLng(), 15);
            marcador.obj.openPopup();
        }
    }
}