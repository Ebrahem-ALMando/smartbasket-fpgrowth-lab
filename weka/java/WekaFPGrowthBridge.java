import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;

import weka.associations.AssociationRule;
import weka.associations.AssociationRules;
import weka.associations.DefaultAssociationRule;
import weka.associations.FPGrowth;
import weka.associations.Item;
import weka.core.Attribute;
import weka.core.Instances;
import weka.core.SelectedTag;
import weka.core.converters.ConverterUtils.DataSource;

/** Auditable WEKA 3.8.7 FPGrowth bridge for the frozen SmartBasket basket. */
public final class WekaFPGrowthBridge {
  private static final int EXPECTED_INSTANCES = 17901;
  private static final int EXPECTED_ATTRIBUTES = 3791;
  private static final long EXPECTED_PRESENCES = 473636L;
  private static final double MIN_SUPPORT = 0.005;
  private static final double MIN_CONFIDENCE = 0.70;
  private static final int MAX_ITEMS = 3;

  private WekaFPGrowthBridge() {}

  private static String jsonEscape(String value) {
    return value.replace("\\", "\\\\").replace("\"", "\\\"")
        .replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t");
  }

  private static String csv(String value) {
    String safe = value == null ? "" : value;
    return "\"" + safe.replace("\"", "\"\"") + "\"";
  }

  private static String jsonArray(Collection<String> values) {
    List<String> quoted = new ArrayList<>();
    for (String value : values) {
      quoted.add("\"" + jsonEscape(value) + "\"");
    }
    return "[" + String.join(",", quoted) + "]";
  }

  private static String jsonArray(String[] values) {
    return jsonArray(Arrays.asList(values));
  }

  private static String jsonArray(double[] values) {
    List<String> serialized = new ArrayList<>();
    for (double value : values) {
      serialized.add(Double.toString(value));
    }
    return "[" + String.join(",", serialized) + "]";
  }

  private static List<String> aliases(Collection<Item> items) throws Exception {
    List<String> result = new ArrayList<>();
    for (Item item : items) {
      if (!"1".equals(item.getItemValueAsString())) {
        throw new IllegalStateException("Rule contains a non-positive nominal item: " + item);
      }
      result.add(item.getAttribute().name());
    }
    result.sort(String::compareTo);
    return result;
  }

  private static double namedMetric(AssociationRule rule, String wanted) throws Exception {
    for (String name : rule.getMetricNamesForRule()) {
      if (name.equalsIgnoreCase(wanted)) {
        return rule.getNamedMetricValue(name);
      }
    }
    throw new IllegalStateException("WEKA rule API does not expose required metric: " + wanted);
  }

  private static long validateInput(Instances data) {
    if (data.numInstances() != EXPECTED_INSTANCES) {
      throw new IllegalStateException("Unexpected instance count: " + data.numInstances());
    }
    if (data.numAttributes() != EXPECTED_ATTRIBUTES) {
      throw new IllegalStateException("Unexpected attribute count: " + data.numAttributes());
    }
    for (int i = 0; i < data.numAttributes(); i++) {
      Attribute attribute = data.attribute(i);
      String expectedAlias = String.format("P_%06d", i);
      if (!attribute.name().equals(expectedAlias) || !attribute.isNominal()
          || attribute.numValues() != 2 || !attribute.value(0).equals("0")
          || !attribute.value(1).equals("1")) {
        throw new IllegalStateException("Invalid binary attribute at index " + i + ": " + attribute);
      }
    }
    long presences = 0;
    for (int i = 0; i < data.numInstances(); i++) {
      int rowPresences = 0;
      for (int j = 0; j < data.instance(i).numValues(); j++) {
        double value = data.instance(i).valueSparse(j);
        if (value != 1.0) {
          throw new IllegalStateException("Sparse row contains value other than nominal index 1");
        }
        rowPresences++;
      }
      if (rowPresences == 0) {
        throw new IllegalStateException("Empty transaction at row " + i);
      }
      presences += rowPresences;
    }
    if (presences != EXPECTED_PRESENCES) {
      throw new IllegalStateException("Unexpected presence count: " + presences);
    }
    return presences;
  }

  private static FPGrowth configuredMiner() {
    FPGrowth miner = new FPGrowth();
    // WEKA documents that sparse instances always use nominal index 1. The public
    // positive index is still set to human-facing value 2 for dense/GUI parity.
    miner.setPositiveIndex(2);
    miner.setMaxNumberOfItems(MAX_ITEMS);
    miner.setNumRulesToFind(1000000);
    miner.setMetricType(new SelectedTag(
        DefaultAssociationRule.METRIC_TYPE.CONFIDENCE.ordinal(),
        DefaultAssociationRule.TAGS_SELECTION));
    miner.setMinMetric(MIN_CONFIDENCE);
    // Python has no upper support ceiling. A diagnostic with upper=0.005
    // returned only rules whose support count was exactly 90.
    miner.setUpperBoundMinSupport(1.0);
    miner.setLowerBoundMinSupport(MIN_SUPPORT);
    miner.setDelta(MIN_SUPPORT);
    miner.setFindAllRulesForSupportLevel(true);
    return miner;
  }

  private static void writeRules(Path output, List<AssociationRule> rules) throws Exception {
    try (PrintWriter writer = new PrintWriter(Files.newBufferedWriter(output, StandardCharsets.UTF_8))) {
      writer.println("rule_index,premise_aliases,consequence_aliases,premise_support_count,"
          + "consequence_support_count,total_support_count,transaction_count,confidence,lift,"
          + "leverage,conviction,primary_metric_name,primary_metric_value,metric_names,"
          + "metric_values,weka_rule_text");
      int index = 0;
      for (AssociationRule rule : rules) {
        String premise = jsonArray(aliases(rule.getPremise()));
        String consequence = jsonArray(aliases(rule.getConsequence()));
        String[] metricNames = rule.getMetricNamesForRule();
        double[] metricValues = rule.getMetricValuesForRule();
        writer.println(index + "," + csv(premise) + "," + csv(consequence) + ","
            + rule.getPremiseSupport() + "," + rule.getConsequenceSupport() + ","
            + rule.getTotalSupport() + "," + rule.getTotalTransactions() + ","
            + Double.toString(namedMetric(rule, "Confidence")) + ","
            + Double.toString(namedMetric(rule, "Lift")) + ","
            + Double.toString(namedMetric(rule, "Leverage")) + ","
            + Double.toString(namedMetric(rule, "Conviction")) + ","
            + csv(rule.getPrimaryMetricName()) + ","
            + Double.toString(rule.getPrimaryMetricValue()) + ","
            + csv(jsonArray(metricNames)) + "," + csv(jsonArray(metricValues)) + ","
            + csv(rule.toString()));
        index++;
      }
    }
  }

  private static void writeEffectiveOptions(Path output, FPGrowth miner) throws Exception {
    String[] options = miner.getOptions();
    String document = "{\n"
        + "  \"weka_class\": \"weka.associations.FPGrowth\",\n"
        + "  \"effective_options_array\": " + jsonArray(options) + ",\n"
        + "  \"positive_index\": " + miner.getPositiveIndex() + ",\n"
        + "  \"sparse_positive_nominal_index_zero_based\": 1,\n"
        + "  \"maximum_items\": " + miner.getMaxNumberOfItems() + ",\n"
        + "  \"requested_number_of_rules\": " + miner.getNumRulesToFind() + ",\n"
        + "  \"metric_type\": \"" + jsonEscape(miner.getMetricType().getSelectedTag().getReadable()) + "\",\n"
        + "  \"minimum_metric\": " + miner.getMinMetric() + ",\n"
        + "  \"upper_minimum_support\": " + miner.getUpperBoundMinSupport() + ",\n"
        + "  \"lower_minimum_support\": " + miner.getLowerBoundMinSupport() + ",\n"
        + "  \"support_delta\": " + miner.getDelta() + ",\n"
        + "  \"find_all_rules\": " + miner.getFindAllRulesForSupportLevel() + "\n"
        + "}\n";
    Files.writeString(output, document, StandardCharsets.UTF_8);
  }

  private static void writeMetadata(Path output, long loadNanos, long miningNanos,
      long exportNanos, long totalNanos, long presences, int ruleCount, FPGrowth miner)
      throws Exception {
    Runtime runtime = Runtime.getRuntime();
    long used = runtime.totalMemory() - runtime.freeMemory();
    String document = "{\n"
        + "  \"status\": \"success\",\n"
        + "  \"instances\": " + EXPECTED_INSTANCES + ",\n"
        + "  \"attributes\": " + EXPECTED_ATTRIBUTES + ",\n"
        + "  \"presence_count\": " + presences + ",\n"
        + "  \"rule_count\": " + ruleCount + ",\n"
        + "  \"loading_seconds\": " + (loadNanos / 1e9) + ",\n"
        + "  \"mining_seconds\": " + (miningNanos / 1e9) + ",\n"
        + "  \"rule_export_seconds\": " + (exportNanos / 1e9) + ",\n"
        + "  \"bridge_total_seconds\": " + (totalNanos / 1e9) + ",\n"
        + "  \"approximate_jvm_used_memory_bytes\": " + used + ",\n"
        + "  \"jvm_max_memory_bytes\": " + runtime.maxMemory() + ",\n"
        + "  \"java_vm_name\": \"" + jsonEscape(System.getProperty("java.vm.name")) + "\",\n"
        + "  \"java_version\": \"" + jsonEscape(System.getProperty("java.version")) + "\",\n"
        + "  \"java_vendor\": \"" + jsonEscape(System.getProperty("java.vendor")) + "\",\n"
        + "  \"java_architecture\": \"" + jsonEscape(System.getProperty("os.arch")) + "\",\n"
        + "  \"runtime_arguments\": " + jsonArray(ManagementFactory.getRuntimeMXBean().getInputArguments()) + "\n"
        + "}\n";
    Files.writeString(output, document, StandardCharsets.UTF_8);
  }

  public static void main(String[] args) {
    if (args.length != 5) {
      System.err.println("Usage: WekaFPGrowthBridge <input.arff> <rules.csv> "
          + "<console.txt> <run_metadata.json> <effective_options.json>");
      System.exit(2);
    }
    long totalStart = System.nanoTime();
    try {
      Path arff = Path.of(args[0]);
      Path rulesCsv = Path.of(args[1]);
      Path consoleOutput = Path.of(args[2]);
      Path metadata = Path.of(args[3]);
      Path effectiveOptions = Path.of(args[4]);
      Files.createDirectories(rulesCsv.toAbsolutePath().getParent());

      long loadStart = System.nanoTime();
      Instances data = DataSource.read(arff.toString());
      long presences = validateInput(data);
      long loadNanos = System.nanoTime() - loadStart;

      FPGrowth miner = configuredMiner();
      writeEffectiveOptions(effectiveOptions, miner);
      long miningStart = System.nanoTime();
      miner.buildAssociations(data);
      long miningNanos = System.nanoTime() - miningStart;

      AssociationRules associationRules = miner.getAssociationRules();
      if (associationRules == null) {
        throw new IllegalStateException("AssociationRules API returned null after mining");
      }
      List<AssociationRule> rules = associationRules.getRules();
      long exportStart = System.nanoTime();
      writeRules(rulesCsv, rules);
      Files.writeString(consoleOutput, miner.toString() + System.lineSeparator(), StandardCharsets.UTF_8);
      long exportNanos = System.nanoTime() - exportStart;
      long totalNanos = System.nanoTime() - totalStart;
      writeMetadata(metadata, loadNanos, miningNanos, exportNanos, totalNanos,
          presences, rules.size(), miner);
      System.out.println("WEKA_BRIDGE_STATUS=success");
      System.out.println("WEKA_RULE_COUNT=" + rules.size());
      System.out.println("WEKA_LOAD_SECONDS=" + (loadNanos / 1e9));
      System.out.println("WEKA_MINING_SECONDS=" + (miningNanos / 1e9));
      System.out.println("WEKA_EXPORT_SECONDS=" + (exportNanos / 1e9));
      System.out.println("WEKA_TOTAL_SECONDS=" + (totalNanos / 1e9));
    } catch (Throwable error) {
      System.err.println("WEKA_BRIDGE_STATUS=failure");
      error.printStackTrace(System.err);
      System.exit(1);
    }
  }
}
