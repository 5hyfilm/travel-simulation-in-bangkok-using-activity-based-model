package org.matsim.contrib.signals.builder;

import com.google.inject.Inject;
import org.matsim.contrib.signals.model.SignalSystemsManager;
import org.matsim.core.mobsim.framework.events.MobsimBeforeSimStepEvent;
import org.matsim.core.mobsim.framework.events.MobsimInitializedEvent;
import org.matsim.core.mobsim.framework.listeners.MobsimBeforeSimStepListener;
import org.matsim.core.mobsim.framework.listeners.MobsimInitializedListener;

/**
 * Throttles the signal update calculation to reduce computational overhead.
 * Especially useful for large-scale simulations with 500k+ agents.
 */
public class ThrottledSignalEngine implements MobsimBeforeSimStepListener, MobsimInitializedListener {
    private final QSimSignalEngine delegate;
    private static int updateInterval = 5; // Default 5s

    public static void setUpdateInterval(int interval) {
        updateInterval = interval;
    }

    @Inject
    public ThrottledSignalEngine(SignalSystemsManager manager) {
        // We create the delegate manually or can inject it if bound
        this.delegate = new QSimSignalEngine(manager);
    }

    @Override
    public void notifyMobsimInitialized(MobsimInitializedEvent event) {
        delegate.notifyMobsimInitialized(event);
    }

    @Override
    public void notifyMobsimBeforeSimStep(MobsimBeforeSimStepEvent event) {
        double time = event.getSimulationTime();
        // Only trigger signal recalculation every N seconds
        // Lämmer logic will hold the current state until the next evaluation
        if (time % updateInterval == 0) {
            delegate.notifyMobsimBeforeSimStep(event);
        }
    }
}
