package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.Controler;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.simwrapper.SimWrapperModule;

public class RunHermesSimulation {

    public static void main(String[] args) {
        // --- 1. โหลดการตั้งค่าจากไฟล์ XML (วิธีที่เพื่อนแนะนำ) ---
        String configFile = "bangkok_cbd_500k_config.xml";
        Config config = ConfigUtils.loadConfig(configFile);

        // --- 2. เตรียม Scenario ---
        Scenario scenario = ScenarioUtils.loadScenario(config);

        // --- 3. รันการจำลองด้วย Controler ---
        Controler controler = new Controler(scenario);
        
        // เพิ่ม SimWrapper สำหรับดูรายงานผลผ่าน Browser (แถมให้เป็นพิเศษ)
        controler.addOverridingModule(new SimWrapperModule());

        System.out.println("Starting Hermes Simulation using config: " + configFile);
        controler.run();
    }
}
