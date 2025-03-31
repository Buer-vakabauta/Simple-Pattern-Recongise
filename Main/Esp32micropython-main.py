
from machine import UART,Pin
import utime,network,socket,asyncio,uselect

IP="192.168.4.2"
PORT=1347
shapes=[]
html=f"""
    <html>
    <head>
        <title>图像识别结果</title>
    </head>
    <body>
        <h1>识别到的图形</h1>
        <li>图形 数字 面积</li>
        <button onclick="window.location.reload();">刷新</button>
    </body>
    </html>
    """

#UART
uart = UART(2, baudrate=115200, rx=13,tx=12,timeout=10)
uart.init(115200)

#WIFI
mywifi=network.WLAN(network.AP_IF)
mywifi.active(True)
mywifi.config(essid='ESP32',password="66666666")
#uart.write(str(mywifi.ifconfig()[0]))打印wifi信息


#VAR

def generate_html(shapes):
    global html
    """ 生成HTML页面 """
    shape_list = "".join(f"<li>{shape}</li>" for shape in shapes[::-1])
    html1 = f"""
    <html>
    <head>
        <title>图像识别结果</title>
    </head>
    <body>
        <h1>识别到的图形</h1>
        <li>图形 数字 面积</li>
        {shape_list}
        <button onclick="window.location.reload();">刷新</button>
    </body>
    </html>
    """
    html=html1
def wait_wificonnect():
    while True:
        device_list=mywifi.status("stations")
        if len(device_list)>=1:
            buffer="WifiConnected info:"+str(device_list)+"\n"
            #uart.write(buffer)
            break
        utime.sleep(1)

def tcp_server_fun():

    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    tcp_server.bind(("",80))
    tcp_server.listen(128)
    response_headers="HTTP/1.1 200 OK\r\n"
    response_headers+="Content-Type:text/html;charset=utf-8\r\n"
    response_headers+="\r\n"
    
    poll=uselect.poll()
    poll.register(tcp_server, uselect.POLLIN)  # 监听 TCP 连接
    poll.register(uart, uselect.POLLIN)  # 监听 UART 串口数据
    while True:
        events=poll.poll(500)
        for sock,event_type in events:
            if sock == tcp_server and event_type & uselect.POLLIN:
                client_socket,client_info=tcp_server.accept()
                response=response_headers+html
                client_socket.send(response.encode("utf-8"))
                client_socket.close()
            elif sock == uart and event_type & uselect.POLLIN:
                if uart.any():
                    global shapes
                    if(len(shapes)>=10):
                        shapes.pop(0)
                    shapes.append(uart.read().decode())
                    print(shapes[-1])
                    generate_html(shapes)   
def main():
    wait_wificonnect()
    print(mywifi.ifconfig()[0])
    tcp_server_fun()
    

main()
