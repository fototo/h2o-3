package hex.faulttolerance;

import water.Key;
import water.Keyed;

import java.util.Set;

public interface Recoverable<T extends Keyed> {
    
    Key<T> getKey();
    
    Set<Key<?>> getDependentKeys();
    
}
