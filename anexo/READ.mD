# Pasos para Ejecutar el Script

## TCP

1. Ejecutar el script principal:
    ```bash
    sudo python3 main.py
    ```

2. Iniciar el servidor `iperf` en `h2`:
    ```bash
    mininet> h2 iperf -s &
    ```

3. Ejecutar Wireshark en `h2`:
    ```bash
    mininet> h2 wireshark &
    ```

4. Iniciar el cliente `iperf` desde `h1`:
    ```bash
    mininet> h1 iperf -c 10.1.0.252 -t 5
    ```

## UDP

1. Iniciar el servidor `iperf` en `h2` con soporte para UDP:
    ```bash
    mininet> h2 iperf -s -u &
    ```

2. Ejecutar Wireshark en `h2`:
    ```bash
    mininet> h2 wireshark &
    ```

3. Iniciar el cliente `iperf` desde `h1` con soporte para UDP:
    ```bash
    mininet> h1 iperf -c 10.1.0.252 -u -t 5
    ```
