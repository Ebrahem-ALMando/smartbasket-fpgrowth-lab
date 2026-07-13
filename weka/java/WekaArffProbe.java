import weka.core.Attribute;
import weka.core.Instances;
import weka.core.converters.ConverterUtils.DataSource;

/** Tiny general-purpose loader used only for ARFF integration validation. */
public final class WekaArffProbe {
  private WekaArffProbe() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 1) {
      throw new IllegalArgumentException("Usage: WekaArffProbe <input.arff>");
    }
    Instances data = DataSource.read(args[0]);
    long storedValues = 0;
    for (int row = 0; row < data.numInstances(); row++) {
      storedValues += data.instance(row).numValues();
    }
    int binaryNominal = 0;
    for (int column = 0; column < data.numAttributes(); column++) {
      Attribute attribute = data.attribute(column);
      if (attribute.isNominal() && attribute.numValues() == 2
          && attribute.value(0).equals("0") && attribute.value(1).equals("1")) {
        binaryNominal++;
      }
    }
    System.out.println("instances=" + data.numInstances());
    System.out.println("attributes=" + data.numAttributes());
    System.out.println("stored_values=" + storedValues);
    System.out.println("binary_nominal_attributes=" + binaryNominal);
  }
}
