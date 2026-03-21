package org.matsim.contrib.signals.builder;

import com.google.inject.Singleton;
import com.google.inject.multibindings.MapBinder;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.matsim.contrib.signals.SignalSystemsConfigGroup;
import org.matsim.contrib.signals.analysis.SignalEvents2ViaCSVWriter;
import org.matsim.contrib.signals.controller.SignalControllerFactory;
import org.matsim.contrib.signals.model.SignalSystemsManager;
import org.matsim.contrib.signals.sensor.DownstreamSensor;
import org.matsim.contrib.signals.sensor.LinkSensorManager;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.network.algorithms.NetworkTurnInfoBuilderI;

import java.util.HashMap;
import java.util.Map;

/**
 * Custom override of the official SignalsModule to bypass the annoying Fast flow capacity update check.
 */
public class SignalsModule extends AbstractModule {
    private static final Logger log = LogManager.getLogger(SignalsModule.class);
    private MapBinder<String, SignalControllerFactory> signalControllerFactoryMultibinder;
    private Map<String, Class<? extends SignalControllerFactory>> signalControllerFactoryClassNames = new HashMap<>();

    public SignalsModule() {
    }

    @Override
    public void install() {
        getConfig().travelTimeCalculator().setSeparateModes(false);
        log.warn("setting travelTimeCalculatur.setSeparateModes to false since otherwise link2link routing does not work (Custom SignalsModule)");
        
        this.signalControllerFactoryMultibinder = MapBinder.newMapBinder(binder(), String.class, SignalControllerFactory.class);
        
        SignalSystemsConfigGroup signalsConfig = ConfigUtils.addOrGetModule(getConfig(), SignalSystemsConfigGroup.GROUP_NAME, SignalSystemsConfigGroup.class);
        String baseDir = System.getProperty("user.dir") + "/";
        signalsConfig.setSignalSystemFile(baseDir + "data/processed/signalSystems.xml");
        signalsConfig.setSignalGroupsFile(baseDir + "data/processed/signalGroups.xml");
        signalsConfig.setSignalControlFile(baseDir + "data/processed/signalControl.xml");
        signalsConfig.setUseSignalSystems(true);

        // FORCE all signal setup manually, even if MATSim thinks signals are "off" (to bypass original SignalsModule)
        if (true) { 
            bind(SignalModelFactory.class).to(SignalModelFactoryImpl.class);
            addControlerListenerBinding().to(SensorBasedSignalControlerListener.class);
            bind(LinkSensorManager.class).in(Singleton.class);
            bind(DownstreamSensor.class).in(Singleton.class);
            
            for (String key : signalControllerFactoryClassNames.keySet()) {
                signalControllerFactoryMultibinder.addBinding(key).to(signalControllerFactoryClassNames.get(key));
            }
            
            bind(SignalSystemsManager.class).toProvider(FromDataBuilder.class).in(Singleton.class);
            addMobsimListenerBinding().to(ThrottledSignalEngine.class);
            // bind(SignalEvents2ViaCSVWriter.class).asEagerSingleton();
            // addControlerListenerBinding().to(SignalEvents2ViaCSVWriter.class);
            // addEventHandlerBinding().to(SignalEvents2ViaCSVWriter.class);
            
            // BYPASS the Fast flow capacity update check! (Removed entirely in this version)
            
            if (getConfig().controller().isLinkToLinkRoutingEnabled()) {
                bind(NetworkTurnInfoBuilderI.class).to(NetworkWithSignalsTurnInfoBuilder.class);
            }
        }
    }

    final void addSignalControllerFactory(String identifier, Class<? extends SignalControllerFactory> signalControllerFactoryClassName) {
        signalControllerFactoryClassNames.put(identifier, signalControllerFactoryClassName);
    }
}
