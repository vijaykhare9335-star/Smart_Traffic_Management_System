import numpy as np

class TrafficDensityPredictor:
    """Lightweight ML predictor for traffic density and adaptive signal timing."""

    def __init__(self):
        self.labels = ["LOW", "MEDIUM", "HIGH"]
        self.label_to_idx = {label: idx for idx, label in enumerate(self.labels)}
        self.weights = None
        self.bias = None
        self._train_model()

    def _build_training_data(self):
        X = []
        y = []

        for count in range(0, 31):
            if count <= 5:
                label = "LOW"
            elif count <= 15:
                label = "MEDIUM"
            else:
                label = "HIGH"

            for trend in [-5, -2, 0, 2, 5]:
                avg = float(max(0, count + trend // 2))
                X.append([float(count), float(trend), avg])
                y.append(self.label_to_idx[label])

        return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)

    @staticmethod
    def _softmax(logits):
        exp = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        return exp / np.sum(exp, axis=1, keepdims=True)

    @staticmethod
    def _one_hot(y, num_classes):
        one_hot = np.zeros((y.shape[0], num_classes), dtype=np.float32)
        one_hot[np.arange(y.shape[0]), y] = 1.0
        return one_hot

    def _train_model(self):
        X, y = self._build_training_data()
        num_features = X.shape[1]
        num_classes = len(self.labels)

        self.weights = np.random.randn(num_classes, num_features).astype(np.float32) * 0.01
        self.bias = np.zeros((num_classes,), dtype=np.float32)

        y_one_hot = self._one_hot(y, num_classes)
        lr = 0.08
        for _ in range(1200):
            logits = X.dot(self.weights.T) + self.bias
            probs = self._softmax(logits)
            grad_logits = probs - y_one_hot
            grad_w = grad_logits.T.dot(X) / X.shape[0]
            grad_b = np.mean(grad_logits, axis=0)
            self.weights -= lr * grad_w
            self.bias -= lr * grad_b

    def predict_density(self, count, trend=0.0, avg=None):
        if avg is None:
            avg = float(count)

        features = np.array([[float(count), float(trend), float(avg)]], dtype=np.float32)
        logits = features.dot(self.weights.T) + self.bias
        probs = self._softmax(logits)[0]
        label_idx = int(np.argmax(probs))
        return self.labels[label_idx], float(np.max(probs))

    def predict_green_time(self, count, trend=0.0, avg=None):
        density, _ = self.predict_density(count, trend, avg)
        if density == "LOW":
            base = 12
        elif density == "MEDIUM":
            base = 20
        else:
            base = 26

        adjustment = int(min(8, max(0, (count - 5) // 3)))
        return base + adjustment
