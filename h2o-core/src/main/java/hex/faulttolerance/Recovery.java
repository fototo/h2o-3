package hex.faulttolerance;

import water.*;
import water.fvec.Frame;
import water.fvec.persist.FramePersist;
import water.fvec.persist.PersistUtils;
import water.util.FileUtils;
import water.util.IcedHashMap;

import java.net.URI;
import java.util.Map;
import java.util.Set;

public class Recovery<T extends Keyed> {

    public static final String REFERENCES_META_FILE_SUFFIX = "_references";

    public enum ReferenceType {
        FRAME, KEYED
    }

    private final String storagePath;

    /**
     * @param storagePath directory to export all the frames to
     */
    public Recovery(String storagePath) {
        this.storagePath = storagePath;
    }

    /**
     * Saves all of the keyed objects used by this Grid's params. Files are named by objects' keys.
     */
    public void exportReferences(final Recoverable<T> r) {
        final Set<Key<?>> keys = r.getDependentKeys();
        final IcedHashMap<String, String> referenceKeyTypeMap = new IcedHashMap<>();
        for (Key<?> k : keys) {
            persistObj(k.get(), storagePath, referenceKeyTypeMap);
        }
        final String framesFilePath = storagePath + "/" + r.getKey() + REFERENCES_META_FILE_SUFFIX;
        final URI framesUri = FileUtils.getURI(framesFilePath);
        PersistUtils.write(framesUri, ab -> ab.put(referenceKeyTypeMap));
    }

    private void persistObj(
        final Keyed<?> o,
        final String exportDir,
        Map<String, String> referenceKeyTypeMap
    ) {
        if (o instanceof Frame) {
            referenceKeyTypeMap.put(o._key.toString(), ReferenceType.FRAME.toString());
            new FramePersist((Frame) o).saveTo(exportDir, true).get();
        } else if (o != null) {
            referenceKeyTypeMap.put(o._key.toString(), ReferenceType.KEYED.toString());
            URI dest = FileUtils.getURI(exportDir + "/" + o._key);
            PersistUtils.write(dest, ab -> ab.putKey(o._key));
        }
    }

    public void loadReferences(final Recoverable<T> r) {
        final URI referencesUri = FileUtils.getURI(storagePath + "/" + r.getKey() + REFERENCES_META_FILE_SUFFIX);
        Map<String, String> referencesMap = PersistUtils.read(referencesUri, AutoBuffer::get);
        final Futures fs = new Futures();
        referencesMap.forEach((key, type) -> {
            switch (ReferenceType.valueOf(type)) {
                case FRAME: 
                    FramePersist.loadFrom(Key.make(key), storagePath).get();
                    break;
                case KEYED:
                    PersistUtils.read(URI.create(storagePath + "/" + key), ab -> ab.getKey(Key.make(key), fs));
                    break;
                default:
                    throw new IllegalStateException("Unknown reference type " + type);
            }
        });
        fs.blockForPending();
    }

}
