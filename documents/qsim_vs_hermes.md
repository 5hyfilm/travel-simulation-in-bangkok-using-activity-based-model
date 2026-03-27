# QSim vs Hermes: MATSim Simulation Engines

MATSim มี simulation engine ให้เลือก 2 ตัวหลัก ซึ่งส่งผลต่อความเร็วและ feature ที่ใช้ได้

---

## ภาพรวม

| คุณสมบัติ | QSim | Hermes |
|-----------|------|--------|
| **ประเภท** | Queue-based simulation | Event-driven simulation |
| **ความเร็ว** | ช้ากว่า | เร็วกว่า (เหมาะกับ agent จำนวนมาก) |
| **หน่วยความจำ** | ใช้มากกว่า | ประหยัดกว่า |
| **Traffic dynamics** | Queue / Kinematic waves | Queue เท่านั้น |
| **Signals / Lämmer** | รองรับ ✅ | ไม่รองรับ ❌ |
| **Lanes** | รองรับ ✅ | ไม่รองรับ ❌ |
| **Replanning** | รองรับ ✅ | รองรับ ✅ |
| **Public transit** | รองรับ ✅ | รองรับ ✅ |
| **เหมาะกับ** | simulation ที่ต้องการ signal / lane | simulation ขนาดใหญ่ที่เน้นความเร็ว |

---

## Hermes เร็วกว่า แต่ feature น้อยกว่า

Hermes เป็นแค่ตัวรัน simulation ให้เร็วขึ้น — **ไม่ได้เปลี่ยนหลักการทำงานของ MATSim** replanning และ iteration ยังทำงานเหมือนเดิมทุกอย่าง แค่แต่ละ iteration เสร็จเร็วขึ้น

ข้อแลกเปลี่ยนคือ Hermes ไม่รองรับ signals contrib ทั้งหมด (`org.matsim.contrib.signals`) ดังนั้นถ้าต้องการ Lämmer หรือ lane-based simulation ต้องใช้ QSim เท่านั้น

---

## Iteration ไม่เกี่ยวกับ Engine

**Iteration** และ **engine** เป็นคนละเรื่องกัน:

- **Engine** (QSim / Hermes) = วิธีที่รถวิ่งใน simulation ในแต่ละ iteration
- **Iteration** = รอบการปรับพฤติกรรมของ agent

ไม่ว่าจะใช้ engine ไหน จำนวน iteration ที่ต้องการเพื่อให้ระบบ converge ก็ยังเท่าเดิม — Hermes แค่ทำให้แต่ละ iteration **เสร็จเร็วขึ้น** เท่านั้น

---

## Iteration ใน MATSim คืออะไร

**1 iteration = 1 วัน** — แต่ละ iteration มี 2 ขั้นตอน:

```
Iteration N
├── 1. Simulation (QSim หรือ Hermes)
│       รถทุกคันวิ่งตาม plan ปัจจุบัน
│       บันทึก events (ติดไฟแดง, ถึงที่หมาย ฯลฯ)
│
└── 2. Replanning
        แต่ละคนตัดสินใจว่าจะเปลี่ยนพฤติกรรมไหม
        เช่น เปลี่ยนเส้นทาง (ReRoute) ถ้าเส้นเดิมติดมาก
        → ได้ plan ใหม่สำหรับ Iteration N+1
```

เป้าหมายคือให้ระบบ **converge สู่สมดุล** — ทุกคนเลือกเส้นทางที่ดีที่สุดสำหรับตัวเองแล้ว ไม่มีใครได้ประโยชน์จากการเปลี่ยนเส้นทางอีก

---

## Iteration ≠ Machine Learning

แม้จะดูคล้ายกัน แต่หลักการต่างกัน:

| | MATSim Iteration | Machine Learning |
|--|-----------------|-----------------|
| **กลไก** | ลองผิดลองถูก (trial & error) | เรียนรู้จาก error แล้ว update weight |
| **ความจำ** | ไม่มีความรู้สะสมข้ามรอบ | model สะสมความรู้จากทุก epoch |
| **เป้าหมาย** | หาสมดุล (equilibrium) | minimize loss function |
| **เมื่อเปลี่ยนสถานการณ์** | ต้องรันใหม่ตั้งแต่ต้น | model อาจ generalize ได้ |
| **จุด converge** | มี — พอ converge แล้วรันเพิ่มไม่ได้ประโยชน์ | ระวัง overfitting |

---

## โปรเจกต์นี้ใช้อะไร

โปรเจกต์นี้ใช้ **QSim** และรัน **0 iteration** (`setLastIteration(0)`) เพราะ:
- ต้องการ Lämmer adaptive signal → บังคับใช้ QSim
- 0 iteration = รัน simulation รอบเดียวโดยไม่มี replanning เหมาะสำหรับดูพฤติกรรมไฟจราจรเบื้องต้นได้เร็ว

---

## อ่านเพิ่มเติม

- Lämmer algorithm: `documents/laemmer_algorithm.md`
- คู่มือการรัน: `MANUAL.md`
