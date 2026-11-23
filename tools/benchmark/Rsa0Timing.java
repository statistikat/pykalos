import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

import jdplus.sa.base.api.ComponentType;
import jdplus.toolkit.base.api.data.DoubleSeq;
import jdplus.toolkit.base.api.modelling.ComponentInformation;
import jdplus.toolkit.base.api.processing.ProcessingLog;
import jdplus.toolkit.base.api.timeseries.TsData;
import jdplus.toolkit.base.api.timeseries.TsPeriod;
import jdplus.toolkit.base.api.timeseries.regression.ModellingContext;
import jdplus.tramoseats.base.api.tramoseats.TramoSeatsSpec;
import jdplus.tramoseats.base.core.tramoseats.TramoSeatsKernel;

/** Time the JD+ public RSA0 fit and materialize the two requested series. */
public final class Rsa0Timing {
    private record Output(double[] adjusted, double[] errors, List<double[]> components) {}
    private static volatile Output sink;

    private static Output fit(TsData series) {
        var kernel = TramoSeatsKernel.of(TramoSeatsSpec.RSA0, new ModellingContext());
        var result = kernel.process(series, new ProcessingLog() {});
        var components = new ArrayList<double[]>();
        var decomposition = result.getDecomposition();
        for (var table : List.of(decomposition.getInitialComponents(), decomposition.getFinalComponents(), result.getFinals())) {
            for (var type : ComponentType.values()) {
                if (type == ComponentType.Undefined) continue;
                for (var info : List.of(ComponentInformation.Value, ComponentInformation.Stdev,
                        ComponentInformation.Forecast, ComponentInformation.StdevForecast,
                        ComponentInformation.Backcast, ComponentInformation.StdevBackcast)) {
                    var row = table.getSeries(type, info);
                    if (row != null) components.add(row.getValues().toArray());
                }
            }
        }
        return new Output(result.getFinals().getSeries(ComponentType.SeasonallyAdjusted, ComponentInformation.Value)
                          .getValues().toArray(), result.getData("y_ef(24)", TsData.class).getValues().toArray(), components);
    }

    private static void printValues(String id, String field, double[] values) {
        var line = new StringBuilder("values ").append(id).append(' ').append(field);
        for (double x : values) line.append(' ').append(HexFormat.of().toHexDigits(Double.doubleToRawLongBits(x)));
        System.out.println(line);
    }

    public static void main(String[] args) throws Exception {
        int warmup = Integer.parseInt(args[1]), samples = Integer.parseInt(args[2]), batch = Integer.parseInt(args[3]);
        Map<String,TsData> inputs = new LinkedHashMap<>();
        String id = "";
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            if (line.startsWith("case ")) id = line.substring(5);
            if (!line.startsWith("input ") || !(id.equals("fit_tr0_air") || id.equals("fit_multi"))) continue;
            String[] fields = line.split(" ");
            var values = new double[Integer.parseInt(fields[3])];
            for (int i = 0; i < values.length; i++)
                values[i] = Double.longBitsToDouble(Long.parseUnsignedLong(fields[i+4], 16));
            inputs.put(id, TsData.of(TsPeriod.monthly(Integer.parseInt(fields[1]), Integer.parseInt(fields[2])),
                                     DoubleSeq.of(values)));
        }
        if (inputs.size() != 2) throw new IllegalArgumentException("missing benchmark fixtures");
        for (int i = 0; i < warmup; i++) for (TsData series : inputs.values()) sink = fit(series);
        for (int i = 0; i < samples; i++) {
            for (var entry : inputs.entrySet()) {
                long start = System.nanoTime();
                for (int j = 0; j < batch; j++) sink = fit(entry.getValue());
                long elapsed = System.nanoTime() - start;
                System.out.printf("sample %s %d%n", entry.getKey(), elapsed);
                if (i == samples - 1) {
                    System.out.printf("rows %s %d %d%n", entry.getKey(), sink.components().size(),
                        sink.components().stream().mapToInt(row -> row.length).sum());
                    printValues(entry.getKey(), "adjusted", sink.adjusted());
                    printValues(entry.getKey(), "errors", sink.errors());
                }
            }
        }
    }
}
