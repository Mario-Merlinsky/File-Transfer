# Redes

## 1. Iniciar la topología en Mininet

Ir hasta la carpeta del proyecto y ejecutar:

```bash
sudo mn --custom topo.py --topo mytopo --mac --switch ovsk --controller=default
```

> Esto crea una topología definida en `topo.py` con switches `ovsk` y asigna direcciones MAC automáticamente.

---

## 2. Obtener las IPs de los hosts

Dentro del entorno de Mininet, ejecutá los siguientes comandos para obtener las IPs de los hosts:

```bash
mininet> h1 ifconfig
mininet> h2 ifconfig
```

---

## 3. Ejecutar los scripts de servidor y cliente

Ir al directorio `src`:

```bash
cd ~/Redes/src
```



### Servidor

Ejecutar en el host correspondiente:

```bash
python3 start-server.py -H 10.0.0.2 -p 7000 -s <ruta_de_almacenamiento_servidor> -r <protocolo>
```

- `-H`: IP del servidor
- `-p`: Puerto
- `-s`: Ruta donde guardar archivos
- `-r`: Protocolo (`stop_and_wait (SW)`  o `go_back_n (GBN)`)



### Cliente - Upload

```bash
python3 upload.py -H 10.0.0.2 -p 7000 -s <ruta_local>/<archivo> -n <nombre_en_servidor> -r <protocolo>
```

- `-s`: Ruta del archivo local a subir
- `-n`: Nombre que tendrá el archivo en el servidor



### Cliente - Download

```bash
python3 download.py -H 10.0.0.2 -p 7000 -d <ruta_de_descarga> -n <nombre_en_servidor> -r <protocolo>
```

- `-d`: Carpeta destino en el cliente
- `-n`: Nombre del archivo a descargar

---

## Aclaraciones

- El servidor debe estar corriendo antes de iniciar una transferencia.
- El protocolo puede ser `stop_and_wait (SW)`  o `go_back_n (GBN)`.
# Anexo

Puedes encontrar información adicional en el [README del anexo](./anexo/README.md).
