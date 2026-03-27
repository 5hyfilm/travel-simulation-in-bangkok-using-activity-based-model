# Signal Placement in the Bangkok Lämmer Simulation

อธิบายวิธีที่โปรเจกต์นี้กำหนดตำแหน่งและโครงสร้างของสัญญาณไฟจราจร เพื่อใช้กับ Lämmer adaptive signal controller ใน MATSim

---

## ภาพรวม

ระบบสัญญาณไฟจราจรถูกสร้างขึ้นโดยอัตโนมัติจากโครงสร้างเครือข่ายถนน (topology) ระหว่างขั้นตอน `ConvertOSM` โดยไม่ได้ใช้แท็ก `highway=traffic_signals` จาก OSM โดยตรง แต่ใช้เกณฑ์เชิง topology แทน

---

## เกณฑ์การเลือก Junction

Junction ใดก็ตามที่ผ่านเงื่อนไขต่อไปนี้จะได้รับการติดตั้งระบบสัญญาณไฟ:

```
(จำนวน incoming links) + (จำนวน outgoing links) > 3
และมี incoming links อย่างน้อย 1 เส้น
```

**เหตุผล:** junction ที่มี degree รวมมากกว่า 3 มักเป็นสี่แยกหรือทางแยกจริงที่มีการตัดกันของกระแสจราจร ซึ่งเหมาะสมกับการติดตั้งไฟจราจร ส่วน node ที่มี degree ≤ 3 มักเป็นจุดเลี้ยวธรรมดาหรือจุดเชื่อมต่อถนนที่ไม่ซับซ้อน

**ข้อจำกัด:** วิธีนี้อาจวางไฟจราจรที่ junction บางจุดที่ไม่มีไฟจราจรในความเป็นจริง และอาจพลาด junction ที่มีไฟจราจรจริงแต่มี degree ≤ 3 ได้

---

## โครงสร้างสัญญาณ

สำหรับ junction แต่ละจุดที่ผ่านเกณฑ์ ระบบจะสร้างข้อมูลใน 3 ระดับดังนี้:

### 1. Signal System (ระดับ Junction)
- 1 junction → 1 `SignalSystem`
- ใช้ **Node ID** ของ junction เป็น System ID

### 2. Signal (ระดับ Link)
- แต่ละ **incoming link** → 1 `Signal`
- Signal อ้างอิงถึง link ที่รถวิ่งเข้ามาหา junction นั้น
- ใช้ **Link ID** เป็น Signal ID

### 3. Signal Group (ระดับเฟส)
- แต่ละ Signal → 1 `SignalGroup` แยกกัน (1 group ต่อ 1 incoming direction)
- ทำให้ Lämmer สามารถควบคุมแต่ละทิศทางเข้าอย่างอิสระ

**ตัวอย่าง:** junction ที่มี 3 incoming links จะได้รับ 1 SignalSystem, 3 Signals, และ 3 SignalGroups

```
Junction Node (id: 12345)
├── SignalSystem: "12345"
│   ├── Signal: "link_A"  → group "12345_1"
│   ├── Signal: "link_B"  → group "12345_2"
│   └── Signal: "link_C"  → group "12345_3"
```

---

## ไฟล์ที่สร้างขึ้น

`ConvertOSM.java` สร้างไฟล์ 3 ไฟล์ใน `data/processed/`:

| ไฟล์ | เนื้อหา |
|------|---------|
| `signalSystems.xml` | ระบุว่ามี SignalSystem ที่ junction ไหน และมี Signal บน link ใดบ้าง |
| `signalGroups.xml` | จัดกลุ่ม Signal เข้าเป็น SignalGroup แต่ละเฟส |
| `signalControl.xml` | กำหนด controller เป็น `LaemmerSignalController` สำหรับทุก system |

---

## การทำความสะอาด Signal ก่อนรัน Simulation

เมื่อ `RunNetworkCleaner` ลบ link ที่ไม่ connected ออกจาก network แล้ว อาจเกิดสถานการณ์ที่ Signal อ้างถึง link ที่ไม่มีอยู่ใน cleaned network อีกต่อไป

`RunLaemmerSimulation.java` จึงเรียกฟังก์ชัน `cleanSignals()` โดยอัตโนมัติก่อนรัน simulation โดยทำ 3 ขั้นตอน:

1. **ลบ Signal** ที่อ้างถึง link ที่หายไปจาก network
2. **ลบ SignalSystem** ที่ไม่มี Signal เหลืออยู่เลย
3. **ลบ SignalGroup** ที่ว่างเปล่า หรือของ system ที่ถูกลบ

> **หมายเหตุ:** ถ้ามีการสร้างหรือแก้ไข network ใหม่ ต้องรัน `ConvertOSM` และ `RunNetworkCleaner` ใหม่ทุกครั้ง เพราะ signal XML จะยังอ้างถึง link ชุดเก่าอยู่

---

## Lämmer Controller

ทุก SignalSystem ใช้ `LaemmerSignalController` ซึ่งเป็น adaptive algorithm ที่:
- คำนวณ "แรงดัน" ของรถที่รอในแต่ละ incoming link แบบ real-time
- ตัดสินใจเปิดไฟเขียวให้ทิศทางที่มีแรงดันสูงสุดก่อน
- ปรับเวลาไฟเขียวโดยอัตโนมัติ ไม่ใช้ตารางเวลาตายตัว

ความถี่ในการคำนวณสามารถปรับได้ใน `RunLaemmerSimulation.java`:
```java
ThrottledSignalEngine.setUpdateInterval(5); // อัปเดตทุก 5 วินาที (default)
```

---

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | บทบาท |
|------|-------|
| `src/main/java/org/matsim/project/ConvertOSM.java` | สร้าง signal XML จาก OSM topology |
| `src/main/java/org/matsim/project/RunLaemmerSimulation.java` | โหลด, clean, และรัน simulation |
| `src/main/java/org/matsim/contrib/signals/builder/ThrottledSignalEngine.java` | ควบคุมความถี่การอัปเดต signal |
| `data/processed/signalSystems.xml` | ตำแหน่ง signal ที่ junction แต่ละจุด |
| `data/processed/signalGroups.xml` | การจัดกลุ่ม signal เป็นเฟส |
| `data/processed/signalControl.xml` | กำหนด controller เป็น Lämmer |
