from board import board_info
from fpioa_manager import fm
from maix import GPIO,KPU
import time,sensor,image,lcd,gc,math
from machine import UART
threshold = [(59, 100, -17, 127, -9, 76)]
od_img = image.Image(size=(224,224))
obj_name = ('2', '0', '3', '4', '5', '6', '7', '1', '8', '9')
anchor = (1.2984, 1.6594, 1.3778, 1.8665, 1.683, 1.858, 1.7373, 1.6094, 2.0576, 1.7039)
img=None
current_test = 1
num=None
fm.register(1, fm.fpioa.UART1_TX)
fm.register(0, fm.fpioa.UART1_RX)
uart1 = UART(UART.UART1, 115200)
lcd.init()
sensor.reset(dual_buff=True)
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((224, 224))
sensor.skip_frames(time = 2000)
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
boot_key = GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_UP)
last_press_time=0
kpu=None
class Shape:
	def __init__(self, shape_type: str=None, number: int = None, area: float = None):
		if shape_type not in {"Triangle", "Square", "Circle", "Rectangle","num"}:
			raise ValueError("Invalid shape type")
		self.shape_type = shape_type
		self.number = number
		self.area = area
	def __str__(self):
		if self.shape_type=='Triangle':
			self.area=self.area*1.53
		else:
			self.area=self.area*1.43
		return "{} {} {}".format(self.shape_type,self.number,self.area)
	def __repr__(self):
		return self.__str__()
def boot_key_irq(pin_num):
	global current_test, last_press_time
	if boot_key.value() == 0:
		last_press_time = time.ticks_ms()
	else:
		press_duration = time.ticks_ms() - last_press_time
		if press_duration > 500:
			current_test = 3
		else:
			current_test = 2 if current_test == 1 else 1
		lcd.draw_string(10, 200, "Switched to test{}".format(current_test), lcd.WHITE, lcd.RED)
		time.sleep_ms(300)
def kpu_init():
	global kpu
	kpu = KPU()
	kpu.load_kmodel("/sd/KPU/detect0-9/nums.kmodel")
	kpu.init_yolo2(anchor, anchor_num=10, img_w=224, img_h=224, net_w=224 , net_h=224 ,layer_w=7 ,layer_h=7, threshold=0.5, nms_value=0.2, classes=10)
def kpu_del():
	kpu.deinit()
def get_num():
	try:
		global img
		global num
		img = sensor.snapshot()
		od_img.draw_image(img, 0, 0)
		od_img.pix_to_ai()
		kpu.run_with_output(od_img)
		dect = kpu.regionlayer_yolo2()
		if len(dect) > 0:
			for l in dect:
				img.draw_rectangle(l[0], l[1], l[2], l[3], color=(0, 255, 0))
				num=obj_name[l[4]]
				img.draw_string(l[0], l[1], num, color=(0, 255, 0), scale=1.5)
				gc.collect()
				return dect
	except Exception as e:
		pass
def distance(p1, p2):
	return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
def get_shape(masked_img):
	try:
		global num
		global img
		result=None
		orgin_img=masked_img.copy()
		blobs = masked_img.find_blobs(threshold, area_threshold=5000)
		del masked_img
		for blob in blobs:
			shape=None
			if(blob.cy()<=15 or blob.pixels()>10000 or blob.pixels()<100):
				continue
			ratio = blob.w() / blob.h()
			area_rate=(blob.w()*blob.h())/blob.pixels()
			if 0.9<area_rate<1.2:
				if 0.9<ratio<1.1:
					shape="Square"
					img.draw_rectangle(blob.rect(), color=127)
					img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
					if not result:
						result=''
					img.draw_rectangle(blob.rect(), color=127)
					img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
					result+=str(Shape(shape,num,blob.pixels()))
					continue
				elif ratio>1.1 or ratio<0.9:
					shape="Rectangle"
					img.draw_rectangle(blob.rect(), color=127)
					img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
					if not result:
						result=''
					img.draw_rectangle(blob.rect(), color=127)
					img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
					result+=str(Shape(shape,num,blob.pixels()))
					continue
			lines = orgin_img.find_lines(roi=(blob.x(),blob.y(),blob.w(),blob.h()),threshold=1000, theta_margin=25, rho_margin=25)
			line_count=len(lines)
			line_theta=[0]
			for l in lines:
				line_theta.append(min(abs(lines[0].theta() - l.theta()), 180 - abs(lines[0].theta() - l.theta())))
			if line_count>=4 and max(line_theta)>80:
				points = []
				for line in lines[:4]:
					points.append((line.x1(), line.y1()))
					points.append((line.x2(), line.y2()))
				if len(points) >= 4:
					dists = []
					for i in range(0, len(points), 2):
						d = distance(points[i], points[i+1])
						dists.append(d)
					avg_len = sum(dists)/len(dists)
					max_len = max(dists)
					min_len = min(dists)
					ratio = max_len / min_len if min_len != 0 else 9999
					if ratio < 1.2:
						shape = "Square"
					elif ratio>1.3:
						shape = "Rectangle"
			elif line_count==3 and 10<=max(line_theta)<=80:
				shape="Triangle"
			elif line_count==0:
				shape="Circle"
			if shape:
				if not result:
					result=''
				img.draw_rectangle(blob.rect(), color=127)
				img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
				result+=str(Shape(shape,num,blob.pixels()))
		if result:
			uart1.write(result)
		return result
		gc.collect()
	except Exception as e:
		img.draw_string(10, 40, str(e), color=(255, 0, 0), scale=1)
def mask_num_area(dect):
	global img
	masked_img=img.copy()
	if not dect:
		return img
	for l in dect:
		x = l[0]
		y = l[1]
		w = l[2]
		h = l[3]
		masked_img.draw_rectangle(x+10, y+15, w-15, h-30, color=(255, 255, 255), fill=True)
	return masked_img
def test1():
	img.draw_string(1,1,"test1")
	get_shape(img)
def test2():
	global num
	get_num()
	uart1.write(str(Shape('num',num,0)))
	img.draw_string(1,1,"test2")
	num=None
def test3():
	global img
	kpu_init()
	while not num:
		r_rect=get_num()
	kpu_del()
	gc.collect()
	while not get_shape(img):
		print(1)
		img=sensor.snapshot()
boot_key.irq(boot_key_irq, GPIO.IRQ_BOTH, GPIO.WAKEUP_NOT_SUPPORT, 7)
while True:
	if current_test == 1:
		img=sensor.snapshot()
		test1()
	elif current_test == 3:
		test3()
		while current_test==3:
			pass
		num=None
	elif current_test == 2:
		kpu_init()
		while current_test==2:
			test2()
			lcd.display(img)
		kpu_del()
		gc.collect()
	lcd.display(img)
	time.sleep(0.1)
	gc.collect()
kpu_del()