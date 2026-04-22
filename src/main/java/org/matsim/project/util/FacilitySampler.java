package org.matsim.project.util;

import org.matsim.api.core.v01.Coord;
import org.matsim.facilities.ActivityFacility;

import java.util.*;

public class FacilitySampler {
    public final Map<String, List<ActivityFacility>> byType;
    public final BBox bbox;
    public final Random rnd;

    private final double centerMinFrac;
    private final double centerMaxFrac;

    public FacilitySampler(Map<String, List<ActivityFacility>> byType, BBox bbox, Random rnd,
                           double centerMinFrac, double centerMaxFrac) {
        this.byType = byType;
        this.bbox = bbox;
        this.rnd = rnd;
        this.centerMinFrac = centerMinFrac;
        this.centerMaxFrac = centerMaxFrac;
    }

    public ActivityFacility sample(String type) {
        List<ActivityFacility> list = byType.getOrDefault(type, List.of());
        if (list.isEmpty()) throw new RuntimeException("No facilities for type=" + type);
        return list.get(rnd.nextInt(list.size()));
    }

    public ActivityFacility sample(String type, Zone zone) {
        List<ActivityFacility> list = byType.getOrDefault(type, List.of());
        if (list.isEmpty()) throw new RuntimeException("No facilities for type=" + type);

        List<ActivityFacility> filtered = new ArrayList<>();
        for (ActivityFacility f : list) {
            if (inZone(f.getCoord(), zone)) filtered.add(f);
        }
        if (filtered.isEmpty()) {
            // fallback กันแผนล้ม
            return sample(type);
        }
        return filtered.get(rnd.nextInt(filtered.size()));
    }

    public boolean inZone(Coord c, Zone z) {
        double x = c.getX(), y = c.getY();

        double cx1 = bbox.minX + bbox.w()*centerMinFrac;
        double cx2 = bbox.minX + bbox.w()*centerMaxFrac;
        double cy1 = bbox.minY + bbox.h()*centerMinFrac;
        double cy2 = bbox.minY + bbox.h()*centerMaxFrac;

        return switch (z) {
            case CENTER -> x>=cx1 && x<=cx2 && y>=cy1 && y<=cy2;
            case LEFT   -> x < bbox.minX + bbox.w()*0.30;
            case RIGHT  -> x > bbox.minX + bbox.w()*0.70;
            case SOUTH  -> y < bbox.minY + bbox.h()*0.30;
            case NORTH  -> y > bbox.minY + bbox.h()*0.70;
            case OUTSIDE-> x<bbox.minX || x>bbox.maxX || y<bbox.minY || y>bbox.maxY;
        };
    }
}
