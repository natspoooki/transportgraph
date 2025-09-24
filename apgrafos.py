import streamlit as st, tempfile, json, random, heapq
from pyvis.network import Network

# clase que representa una estación de transporte
class Estacion:
    def __init__(self,id,nombre,tipo="tren"):
        self.id=id
        self.nombre=nombre
        self.tipo=tipo
        self.conexiones=[]  # lista de conexiones con otras estaciones
    def agregar_conexion(self,e,p):
        # agrega una conexión a otra estación con un peso (tiempo)
        if all(x!=e for x,_ in self.conexiones):
            self.conexiones.append((e,p))
    def eliminar_conexion(self,e):
        # elimina una conexión con otra estación
        self.conexiones=[(x,p) for x,p in self.conexiones if x!=e]

# clase que representa toda la red de transporte
class RedDeTransporte:
    def __init__(self):
        self.estaciones=[]
        self.rutas=[]
    def agregar_estacion(self,e):
        # agrega una estación a la red
        if e not in self.estaciones:
            self.estaciones.append(e)
    def eliminar_estacion(self,e):
        # elimina una estación y todas sus conexiones
        if e in self.estaciones:
            self.estaciones.remove(e)
            for est in self.estaciones:
                est.eliminar_conexion(e)
            self.rutas=[(a,b,p) for a,b,p in self.rutas if a!=e and b!=e]
    def agregar_ruta(self,a,b,p=None):
        # agrega una ruta (con tiempo aleatorio si no se especifica)
        if p is None: p=random.randint(3,15)
        if not any((x==a and y==b) or (x==b and y==a) for x,y,_ in self.rutas):
            self.rutas.append((a,b,p))
            a.agregar_conexion(b,p)
            b.agregar_conexion(a,p)
    def eliminar_ruta(self,a,b):
        # elimina la ruta entre dos estaciones
        self.rutas=[(x,y,p) for x,y,p in self.rutas if not ((x==a and y==b) or (x==b and y==a))]
        a.eliminar_conexion(b)
        b.eliminar_conexion(a)
    def a_dict(self):
        # convierte la red en un diccionario para guardar en json
        return {"nodes":[{"id":e.id,"nombre":e.nombre} for e in self.estaciones],
                "edges":[{"from":a.nombre,"to":b.nombre,"peso":p} for a,b,p in self.rutas]}
    def from_dict(self,data):
        # carga la red desde un diccionario json
        self.estaciones=[]
        self.rutas=[]
        m={}
        for n in data.get("nodes",[]):
            e=Estacion(n["id"],n["nombre"])
            self.agregar_estacion(e)
            m[n["nombre"]]=e
        for ed in data.get("edges",[]):
            self.agregar_ruta(m[ed["from"]], m[ed["to"]], ed["peso"])
    def todas_rutas_mas_rapidas(self, origen, destino, max_paths=300):
        # usa dijkstra para calcular la distancia mínima entre origen y destino
        dist={e.nombre:float("inf") for e in self.estaciones}
        dist[origen.nombre]=0
        pq=[(0,origen.nombre)]
        adj={}
        for a,b,p in self.rutas:
            adj.setdefault(a.nombre,[]).append((b.nombre,p))
            adj.setdefault(b.nombre,[]).append((a.nombre,p))
        while pq:
            d,u=heapq.heappop(pq)
            if d>dist[u]: continue
            for v,w in adj.get(u,[]):
                nd=d+w
                if nd<dist[v]:
                    dist[v]=nd
                    heapq.heappush(pq,(nd,v))
        if dist[destino.nombre]==float("inf"): return [], float("inf")
        # reconstruye todos los caminos mínimos
        preds={n:[] for n in dist}
        for u in adj:
            for v,w in adj[u]:
                if abs(dist[u]+w-dist[v])<1e-9:
                    preds[v].append(u)
        paths=[]
        def dfs(cur, acc):
            if len(paths)>=max_paths: return
            if cur==origen.nombre:
                paths.append(list(reversed(acc+[cur])))
                return
            for p in preds[cur]: dfs(p, acc+[cur])
        dfs(destino.nombre, [])
        return paths, dist[destino.nombre]

# función que genera el html del grafo con pyvis
def generar_html(red, origen=None, destino=None):
    net = Network(height="650px", width="100%", directed=False, bgcolor="#0D0D0D", font_color="white")
    net.force_atlas_2based()
    pastel_colors = ["#FFD580", "#A0E7E5", "#B9FBC0", "#FFAEBC", "#B5BFD9", "#FFC6FF", "#C9F0FF", "#FFFACD"]
    default_node_color = "#1E1E1E"
    start_end_color = "#FF9F1C"
    end_node_color = "#2EC4B6"
    # añade los nodos
    for e in red.estaciones:
        net.add_node(e.nombre, label=e.nombre, title=f"{e.tipo} ({len(e.conexiones)})",
                     color={"background": default_node_color, "border": "#888888"},
                     font={"color": "white", "size": 16}, shadow=True)
    highlight_edges = set()
    node_colors = {}
    # colorea los caminos más rápidos si se da origen y destino
    if origen and destino:
        paths, _ = red.todas_rutas_mas_rapidas(origen, destino)
        for i, path in enumerate(paths[:8]):
            color = pastel_colors[i % len(pastel_colors)]
            for j in range(len(path)-1):
                n1, n2 = path[j], path[j+1]
                highlight_edges.add((n1, n2, color))
                if path[j] not in [origen.nombre, destino.nombre]:
                    node_colors[path[j]] = color
            if path[-1] not in [origen.nombre, destino.nombre]:
                node_colors[path[-1]] = color
        node_colors[origen.nombre] = start_end_color
        node_colors[destino.nombre] = end_node_color
    # añade las aristas (rutas) con color y grosor
    for a,b,p in red.rutas:
        color = "#555555"
        width = 2
        glow = False
        for n1,n2,c in highlight_edges:
            if (a.nombre==n1 and b.nombre==n2) or (a.nombre==n2 and b.nombre==n1):
                color = c
                width = 4
                glow = True
                break
        net.add_edge(a.nombre, b.nombre, value=p, title=f"{p} min", color=color, width=width, smooth=True, shadow=glow)
    # aplica colores a los nodos resaltados
    for nod in red.estaciones:
        if nod.nombre in node_colors:
            net.get_node(nod.nombre)["color"]["background"] = node_colors[nod.nombre]
            net.get_node(nod.nombre)["shadow"] = True
    # opciones visuales
    net.set_options("""
    var options = {
      "nodes": {"borderWidth": 2,"borderWidthSelected": 3,"shadow": true,
                "color": {"border":"#AAAAAA","background":"#1E1E1E"},
                "font": {"color":"white","size":16}},
      "edges": {"color": {"color":"#555555"}, "smooth": { "type":"continuous" }, "shadow": true},
      "physics": {"enabled": true,"stabilization": false,
                  "barnesHut": {"gravitationalConstant": -5000,"centralGravity":0.3,"springLength":100,"springConstant":0.05,"damping":0.09,"avoidOverlap":1}},
      "interaction": {"hover": true, "tooltipDelay":100},
      "layout": {"improvedLayout": false},
      "manipulation": false
    }
    """)
    # guarda el grafo en un archivo temporal html
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.save_graph(tmp.name)
    return tmp.name

# función que crea una red de ejemplo para demo
def crear_demo_red():
    r=RedDeTransporte()
    nombres=["A","B","C","D","E","F","G"]
    estaciones=[Estacion(i+1,n) for i,n in enumerate(nombres)]
    for e in estaciones: r.agregar_estacion(e)
    rutas=[(0,1,3),(1,2,4),(0,2,5),(2,3,2),(3,4,3),(1,4,7),(4,5,2),(5,6,3),(3,6,6)]
    for a,b,p in rutas: r.agregar_ruta(estaciones[a],estaciones[b],p)
    return r, estaciones[0], estaciones[4]

# configuración de la app en streamlit
st.set_page_config(layout="wide")
st.title("Red de Transporte - Tomás Carvajal y Fabiola Chacón")

# inicializa la red de demo en la sesión
if "red" not in st.session_state:
    demo_red, default_o, default_d = crear_demo_red()
    st.session_state.red = demo_red
    st.session_state.default_o = default_o
    st.session_state.default_d = default_d

r=st.session_state.red
default_o=st.session_state.default_o
default_d=st.session_state.default_d

# columna izquierda: edición de la red
col1, col2=st.columns([1,3])
with col1:
    st.subheader("Editar red")
    # botón para borrar toda la red
    if st.button("Borrar todo"):
        st.session_state.red=RedDeTransporte()
        st.success("Red eliminada")
        r=st.session_state.red
    # agregar estación
    new_name=st.text_input("Nueva estación")
    if st.button("Agregar estación"):
        if new_name.strip():
            nid=max([e.id for e in r.estaciones] or [0])+1
            r.agregar_estacion(Estacion(nid,new_name.strip()))
    # agregar ruta
    names=[e.nombre for e in r.estaciones]
    from_sel=st.selectbox("Desde", [""]+names)
    to_sel=st.selectbox("Hasta", [""]+names)
    peso=st.number_input("Tiempo (min)", min_value=1, value=5)
    if st.button("Agregar ruta"):
        if from_sel and to_sel and from_sel!=to_sel:
            A=next((x for x in r.estaciones if x.nombre==from_sel), None)
            B=next((x for x in r.estaciones if x.nombre==to_sel), None)
            if A and B: r.agregar_ruta(A,B,int(peso))
    # eliminar estación
    st.subheader("Eliminar estación")
    del_sel=st.selectbox("Seleccionar estación a eliminar", [""]+names)
    if st.button("Eliminar estación"):
        if del_sel:
            E=next((x for x in r.estaciones if x.nombre==del_sel), None)
            if E:
                r.eliminar_estacion(E)
                st.success(f"Estación {del_sel} eliminada")
    # eliminar ruta
    st.subheader("Eliminar ruta")
    from_del=st.selectbox("Desde (eliminar ruta)", [""]+names, key="from_del")
    to_del=st.selectbox("Hasta (eliminar ruta)", [""]+names, key="to_del")
    if st.button("Eliminar ruta"):
        if from_del and to_del and from_del!=to_del:
            A=next((x for x in r.estaciones if x.nombre==from_del), None)
            B=next((x for x in r.estaciones if x.nombre==to_del), None)
            if A and B:
                r.eliminar_ruta(A,B)
                st.success(f"Ruta {from_del} → {to_del} eliminada")
    # guardar red en json
    if st.button("Guardar JSON"):
        fn=st.text_input("Nombre archivo", value="red.json")
        with open(fn,"w",encoding="utf8") as f: json.dump(r.a_dict(),f,ensure_ascii=False,indent=2)
        st.success(f"Guardado {fn}")
    # cargar red desde json
    upload=st.file_uploader("Cargar JSON", type=["json"])
    if upload:
        data=json.load(upload)
        r.from_dict(data)
        st.success("Red cargada")

# columna derecha: consulta y visualización
with col2:
    st.subheader("Consulta y visualización")
    st.markdown("**El grosor de cada borde representa su tiempo de viaje, hover sobre uno para ver su valor**")
    st.markdown("El grafo es interactivo! Prueba arrastrar un nodo con tu mouse")
    names = [e.nombre for e in r.estaciones]
    origen = st.selectbox("Origen (consulta)", [""]+names, index=names.index(default_o.nombre)+1)
    destino = st.selectbox("Destino (consulta)", [""]+names, index=names.index(default_d.nombre)+1)
    o = next((x for x in r.estaciones if x.nombre==origen), None)
    d = next((x for x in r.estaciones if x.nombre==destino), None)
    # lista de colores pastel para las rutas
    pastel_colors = [
        {"name": "Amarillo Pastel", "hex": "#FFD580"},
        {"name": "Celeste Pastel",  "hex": "#A0E7E5"},
        {"name": "Verde Menta",     "hex": "#B9FBC0"},
        {"name": "Rosa Pastel",     "hex": "#FFAEBC"},
        {"name": "Lavanda Pastel",  "hex": "#B5BFD9"},
        {"name": "Lila Pastel",     "hex": "#FFC6FF"},
        {"name": "Azul Cielo",      "hex": "#C9F0FF"},
        {"name": "Crema Pastel",    "hex": "#FFFACD"}
    ]
    # cálculo de las rutas más rápidas
    paths, total_time = r.todas_rutas_mas_rapidas(o, d)
    if paths:
        info = f"**Tiempo total más rápido:** {total_time} min\n\n**Rutas más rápidas:**\n"
        for i, path in enumerate(paths[:8], 1):
            color_info = pastel_colors[(i-1) % len(pastel_colors)]
            color_name = color_info["name"]
            info += f"{i}. {' → '.join(path)} (Color: {color_name})\n"
        st.info(info)
    # renderiza el grafo en html dentro de streamlit
    fn = generar_html(r, o, d)
    st.components.v1.html(open(fn, "r", encoding="utf8").read(), height=650, scrolling=True)
